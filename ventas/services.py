# ventas/services.py
import re
import unicodedata

from django.db import transaction

from inventario.models import Producto, Tienda

from .models import ItemVenta, Venta


class VentaService:
    """Contiene la lógica de negocio pura para registrar ventas."""

    @staticmethod
    def registrar(
        tienda_id: int, items_data: list, mesa: str = "", pago: str = "efectivo"
    ) -> Venta:
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
            venta = Venta.objects.create(tienda=tienda, total=0, mesa=mesa, pago=pago)
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
    # 1. Mapeo de números hablados a enteros
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

    # 2. Los tamaños reales de la carta El Trebol
    TAMANOS = ["porcion", "personal", "small", "familiar"]

    # 3. Diccionario: Lo que el cliente dice -> Como está en la BD
    SABORES_MAP = {
        "perro": "Perro",
        "texana": "Texana",
        "4 carnes": "4 Carnes",
        "cuatro carnes": "4 Carnes",
        "vegetariana": "Vegetariana",
        "soledana": "Soledaña",
        "caribena": "Caribeña",
        "caprichosa": "Caprichosa",
        "pollo jamon": "Pollo Jamón",
        "pollo champinon": "Pollo Champiñón",
        "peperoni americano": "Peperoni Americano",
        "peperoni salami": "Peperoni Salami",
        "pollo": "Pollo",
        "jamon": "Jamón",
        "bocadillo": "Bocadillo",
        "tomate": "Tomate",
        "salami": "Salami",
        "pina": "Piña",
        "jamon salami": "Jamón Salami",
    }

    @staticmethod
    def limpiar_texto(texto):
        """Quita tildes y pasa todo a minúsculas para no pelear con la ortografía"""
        texto = (
            unicodedata.normalize("NFKD", texto)
            .encode("ASCII", "ignore")
            .decode("utf-8")
        )
        return texto.lower().strip()

    @staticmethod
    def parse(texto: str) -> list:
        texto_limpio = VozParser.limpiar_texto(texto)

        # A. Extraer la cantidad (1 por defecto)
        cantidad = VozParser._extraer_cantidad(texto_limpio)

        # B. Extraer el tamaño
        tamano_detectado = "Personal"  # Valor por defecto
        for t in VozParser.TAMANOS:
            if t in texto_limpio:
                tamano_detectado = "Porción" if t == "porcion" else t.capitalize()
                break

        # C. Ordenamos los sabores de más largos a más cortos para evitar confusiones
        # (ej: que no confunda "Pollo Jamón" con solo "Pollo")
        sabores_hablados = sorted(VozParser.SABORES_MAP.keys(), key=len, reverse=True)

        # ==========================================
        # CASO 1: PIDIERON MITAD Y MITAD
        # ==========================================
        if "mitad" in texto_limpio:
            sabores_encontrados = []
            for sh in sabores_hablados:
                # Si el sabor está en el texto, lo guardamos y lo borramos del texto
                # para no agarrarlo dos veces por error
                if sh in texto_limpio:
                    sabores_encontrados.append(VozParser.SABORES_MAP[sh])
                    texto_limpio = texto_limpio.replace(sh, "", 1)

            if len(sabores_encontrados) >= 2:
                fl1, fl2 = sabores_encontrados[0], sabores_encontrados[1]
                if tamano_detectado == "Porción":
                    raise ValueError("No se puede hacer mitad y mitad en porciones.")

                nombre_bd = f"Pizza Mitad y Mitad - {tamano_detectado}"
                try:
                    prod = Producto.objects.get(nombre__iexact=nombre_bd)
                    return [
                        {
                            "producto_id": prod.id,
                            "cantidad": cantidad,
                            "nota": f"½ {fl1} y ½ {fl2}",
                        }
                    ]
                except Producto.DoesNotExist:
                    raise ValueError(
                        f"No hay combos mitad y mitad tamaño {tamano_detectado}."
                    )
            else:
                raise ValueError(
                    "Escuché 'mitad' pero no me quedaron claros los dos sabores."
                )

        # ==========================================
        # CASO 2: PIDIERON UNA PIZZA ENTERA
        # ==========================================
        sabor_detectado = None
        for sh in sabores_hablados:
            if sh in texto_limpio:
                sabor_detectado = VozParser.SABORES_MAP[sh]
                break  # Agarramos el primero (el más largo) y paramos

        if sabor_detectado:
            nombre_bd = f"Pizza {sabor_detectado} - {tamano_detectado}"
            try:
                prod = Producto.objects.get(nombre__iexact=nombre_bd)
                return [{"producto_id": prod.id, "cantidad": cantidad}]
            except Producto.DoesNotExist:
                raise ValueError(f"No encontré la {nombre_bd} en la base de datos.")

        # ==========================================
        # CASO 3: ADICIONALES (Bordes)
        # ==========================================
        if "borde" in texto_limpio:
            if "queso" in texto_limpio:
                nombre_bd = f"Adicional Borde de Queso - {tamano_detectado}"
            elif "bocadillo" in texto_limpio:
                nombre_bd = f"Adicional Borde de Bocadillo - {tamano_detectado}"

            try:
                prod = Producto.objects.get(nombre__iexact=nombre_bd)
                return [{"producto_id": prod.id, "cantidad": cantidad}]
            except:
                raise ValueError(f"No encontré el borde {tamano_detectado}.")

        # Si llega hasta aquí, habló carreta y no se entendió
        raise ValueError("No entendí de qué sabor o tamaño la quieres, repite porfa.")

    @staticmethod
    def _extraer_cantidad(texto):
        # Busca números en dígitos ("2")
        digitos = re.search(r"\b(\d+)\b", texto)
        if digitos:
            return int(digitos.group(1))

        # Busca números en palabras ("dos") usando boundaries (\b) para no confundir
        for palabra, num in VozParser.PALABRAS_NUMEROS.items():
            if re.search(rf"\b{palabra}\b", texto):
                return num
        return 1
