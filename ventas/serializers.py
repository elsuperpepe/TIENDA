"""
from rest_framework import serializers

from .models import Tienda


class TiendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tienda
        fields = "__all__"  # Esto traduce todos los campos de la tienda a JSON
"""

# ventas/serializers.py
from rest_framework import serializers

from inventario.models import Producto, Tienda


class ItemVentaEntradaSerializer(serializers.Serializer):
    producto_id = serializers.PrimaryKeyRelatedField(queryset=Producto.objects.all())
    cantidad = serializers.IntegerField(min_value=1)


class VentaEntradaSerializer(serializers.Serializer):
    tienda_id = serializers.PrimaryKeyRelatedField(queryset=Tienda.objects.all())
    items = ItemVentaEntradaSerializer(many=True)

    def validate_items(self, value):
        if len(value) == 0:
            raise serializers.ValidationError("Debe haber al menos un producto.")
        return value
