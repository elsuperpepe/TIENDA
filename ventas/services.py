# ventas/services.py
import re

from django.db import transaction

from inventario.models import Producto, Tienda

from .models import ItemVenta, Venta


class VentaService:
    """Contiene la lógica de negocio pura para registrar ventas."""

    @staticmethod
    def registrar(tienda_id: int, items_data: list) -> Venta:
        """
        Registra una venta, descuenta stock y devuelve la Venta creada.
        items_data: lista de diccionarios con 'producto_id' (int o instancia) y 'cantidad' (int).
        """
        tienda = Tienda.objects.get(id=tienda_id)

        with transaction.atomic():
            # 1. Bloquear productos implicados
            ids_productos = [
                item["producto_id"]
                if isinstance(item["producto_id"], int)
                else item["producto_id"].id
                for item in items_data
            ]
            productos = (
                Producto.objects.select_for_update()
                .filter(id__in=ids_productos)
                .order_by("id")
            )

            # 2. Validar stock solo para productos físicos
            for item in items_data:
                producto_id = (
                    item["producto_id"]
                    if isinstance(item["producto_id"], int)
                    else item["producto_id"].id
                )
                producto = productos.get(id=producto_id)
                if not producto.es_servicio:
                    if producto.stock < item["cantidad"]:
                        raise ValueError(
                            f"Stock insuficiente para '{producto.nombre}'. "
                            f"Disponible: {producto.stock}, solicitado: {item['cantidad']}."
                        )

            # 3. Crear la venta
            venta = Venta.objects.create(tienda=tienda, total=0)

            total_venta = 0
            for item in items_data:
                producto_id = (
                    item["producto_id"]
                    if isinstance(item["producto_id"], int)
                    else item["producto_id"].id
                )
                producto = productos.get(id=producto_id)
                cantidad = item["cantidad"]
                precio_unitario = producto.precio
                subtotal = precio_unitario * cantidad
                nota = item.get("nota", "")

                ItemVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                    nota=nota,
                )

                if not producto.es_servicio:
                    producto.stock -= cantidad
                    producto.save()

                total_venta += subtotal

            venta.total = total_venta
            venta.save()

        return venta

    @staticmethod
    def void(venta_id: int):
        """Anula una venta, restaura stock y la marca como cancelada."""
        venta = Venta.objects.get(id=venta_id)
        if venta.cancelada:
            raise ValueError("La venta ya está anulada.")
        with transaction.atomic():
            for item in venta.items.all():
                if not item.producto.es_servicio:
                    item.producto.stock += item.cantidad
                    item.producto.save()
            venta.cancelada = True
            venta.save()
        return venta


class VozParser:
    PALABRAS_NUMEROS = {
        "un": 1,
        "una": 1,
        "uno": 1,
        "dos": 2,
        "tres": 3,
        "cuatro": 4,
        "cinco": 5,
        "seis": 6,
        "siete": 7,
        "ocho": 8,
        "nueve": 9,
        "diez": 10,
    }
    TAMANOS = {
        "personal": "Personal",
        "mediana": "Mediana",
        "grande": "Grande",
        "extragrande": "Extragrande",
    }

    @staticmethod
    def parse(texto: str) -> list:
        texto = texto.lower().strip()
        # Buscar patrón mitades: <tamaño> mitad <flavor1> (y|,) mitad <flavor2>
        # Ej: "mediana mitad perro y mitad hawaiana"
        # Usamos regex simple
        import re

        mitad_match = re.search(
            r"(personal|mediana|grande|extragrande)\s+mitad\s+(\w+)\s+y\s+mitad\s+(\w+)",
            texto,
        )
        if mitad_match:
            tamanio_nombre = mitad_match.group(1)
            fl1 = mitad_match.group(2)
            fl2 = mitad_match.group(3)
            tamanio_key = VozParser.TAMANOS.get(tamanio_nombre)
            if tamanio_key:
                # Buscar producto "Pizza Mitad y Mitad - <Tamaño>"
                try:
                    prod_mitad = Producto.objects.get(nombre__icontains="mitad y mitad")
                    # Adicionalmente nos aseguramos de que contenga el tamaño
                    if tamanio_key.lower() not in prod_mitad.nombre.lower():
                        raise ValueError(
                            f"No se encontró Pizza Mitad y Mitad de tamaño {tamanio_key}"
                        )
                    return [
                        {
                            "producto_id": prod_mitad.id,
                            "cantidad": 1,
                            "nota": f"mitad {fl1}, mitad {fl2}",
                        }
                    ]
                except Producto.DoesNotExist:
                    raise ValueError(
                        f"No existe producto Mitad y Mitad para tamaño {tamanio_key}"
                    )
        # Si no es mitades, buscar productos normales (como antes)
        items = []
        for producto in Producto.objects.all():
            palabras_clave = producto.nombre.lower().split()
            coincidencias = sum(1 for palabra in palabras_clave if palabra in texto)
            if coincidencias >= 1:
                cantidad = VozParser._extraer_cantidad(texto, producto.nombre.lower())
                if cantidad > 0:
                    items.append({"producto_id": producto.id, "cantidad": cantidad})
        if not items:
            raise ValueError("No se encontraron productos en el texto.")
        return items

    @staticmethod
    def _extraer_cantidad(texto, nombre_producto):
        digitos = re.search(r"\b(\d+)\b", texto)
        if digitos:
            return int(digitos.group(1))
        for palabra in VozParser.PALABRAS_NUMEROS:
            if palabra in texto:
                return VozParser.PALABRAS_NUMEROS[palabra]
        return 1
