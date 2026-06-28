# ventas/serializers.py
from rest_framework import serializers

from inventario.models import Producto, Tienda


class ItemVentaEntradaSerializer(serializers.Serializer):
    producto_id = serializers.PrimaryKeyRelatedField(queryset=Producto.objects.all())
    cantidad = serializers.IntegerField(min_value=1)
    nota = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )


class VentaEntradaSerializer(serializers.Serializer):
    tienda_id = serializers.PrimaryKeyRelatedField(queryset=Tienda.objects.all())
    items = ItemVentaEntradaSerializer(many=True)

    def validate_items(self, value):
        if len(value) == 0:
            raise serializers.ValidationError("Debe haber al menos un producto.")
        return value
