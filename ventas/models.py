from django.db import models

from inventario.models import Producto, Tienda


class Venta(models.Model):
    tienda = models.ForeignKey(Tienda, on_delete=models.CASCADE)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha = models.DateTimeField(auto_now_add=True)
    cancelada = models.BooleanField(default=False)
    cerrada = models.BooleanField(default=False)
    # nota a nivel de venta (opcional, para comentarios generales)
    nota = models.CharField(max_length=255, blank=True, default="")
    mesa = models.CharField(max_length=50, blank=True, default="")
    pago = models.CharField(max_length=20, default="efectivo")

    def __str__(self):
        return f"Venta #{self.id} — ${self.total} ({'anulada' if self.cancelada else 'activa'})"


class ItemVenta(models.Model):
    venta = models.ForeignKey(Venta, related_name="items", on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # nota a nivel de item — para "½ perro + ½ hawaiana", etc.
    nota = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        base = f"{self.cantidad}x {self.producto.nombre}"
        return f"{base} ({self.nota})" if self.nota else base
