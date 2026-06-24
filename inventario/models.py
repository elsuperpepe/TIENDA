from django.db import models


class Tienda(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    es_servicio = models.BooleanField(default=False)  # ← añade esta línea

    def __str__(self):
        return self.nombre
