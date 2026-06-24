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

                ItemVenta.objects.create(
                    venta=venta,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                )

                if not producto.es_servicio:
                    producto.stock -= cantidad
                    producto.save()

                total_venta += subtotal

            venta.total = total_venta
            venta.save()

        return venta


class VozParser:
    """Convierte texto dictado a items de venta."""

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

    @staticmethod
    def parse(texto: str) -> list:
        texto = texto.lower().strip()
        items = []
        for producto in Producto.objects.all():
            # Dividimos el nombre en palabras clave (ej: ["alquiler", "xbox", "(hora)"])
            palabras_clave = producto.nombre.lower().split()
            # Buscamos cuántas de esas palabras aparecen en el texto
            coincidencias = sum(1 for palabra in palabras_clave if palabra in texto)
            if coincidencias >= 1:  # Al menos una palabra coincide
                cantidad = VozParser._extraer_cantidad(texto, producto.nombre.lower())
                if cantidad > 0:
                    items.append({"producto_id": producto.id, "cantidad": cantidad})
        if not items:
            raise ValueError("No se encontraron productos en el texto.")
        return items

    @staticmethod
    def _extraer_cantidad(texto: str, nombre_producto: str) -> int:
        # Buscar un número (dígito o palabra) en todo el texto
        # Primero buscamos dígitos
        digitos = re.search(r"\b(\d+)\b", texto)
        if digitos:
            return int(digitos.group(1))
        # Luego buscamos palabras numéricas
        for palabra in VozParser.PALABRAS_NUMEROS:
            if palabra in texto:
                return VozParser.PALABRAS_NUMEROS[palabra]
        # Si no hay cantidad explícita, asumimos 1
        return 1
