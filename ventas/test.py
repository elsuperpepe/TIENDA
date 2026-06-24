# ventas/tests.py
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from inventario.models import Producto, Tienda

from .models import ItemVenta, Venta


class RegistrarVentaTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tienda = Tienda.objects.create(nombre="Tienda Test")
        self.producto = Producto.objects.create(nombre="Café", precio=5.00, stock=10)
        self.url = reverse("registrar-venta")  # necesitamos darle nombre a la ruta

    def test_venta_exitosa_descuenta_stock(self):
        datos = {
            "tienda_id": self.tienda.id,
            "items": [{"producto_id": self.producto.id, "cantidad": 2}],
        }
        respuesta = self.client.post(self.url, datos, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 8)  # 10 - 2
        venta = Venta.objects.first()
        self.assertEqual(float(venta.total), 10.00)

    def test_stock_insuficiente_rechaza(self):
        datos = {
            "tienda_id": self.tienda.id,
            "items": [{"producto_id": self.producto.id, "cantidad": 20}],
        }
        respuesta = self.client.post(self.url, datos, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)  # stock sin cambios
        self.assertEqual(Venta.objects.count(), 0)

    def test_producto_no_existe(self):
        datos = {
            "tienda_id": self.tienda.id,
            "items": [{"producto_id": 999, "cantidad": 1}],
        }
        respuesta = self.client.post(self.url, datos, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_items_vacio(self):
        datos = {"tienda_id": self.tienda.id, "items": []}
        respuesta = self.client.post(self.url, datos, format="json")
        self.assertEqual(respuesta.status_code, status.HTTP_400_BAD_REQUEST)
