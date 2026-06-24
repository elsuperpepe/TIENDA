from django.db import models

# En ventas/models.py
from inventario.models import Producto, Tienda  # Importamos desde la nueva ubicación


class Venta(models.Model):
    tienda = models.ForeignKey(Tienda, on_delete=models.CASCADE)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha = models.DateTimeField(auto_now_add=True)


class ItemVenta(models.Model):
    venta = models.ForeignKey(Venta, related_name="items", on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0)
