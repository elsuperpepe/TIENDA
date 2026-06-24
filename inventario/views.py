# inventario/views.py
from rest_framework import viewsets

from .models import Producto, Tienda
from .serializers import ProductoSerializer, TiendaSerializer


class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer


class TiendaViewSet(viewsets.ModelViewSet):  # puede que ya lo tengas
    queryset = Tienda.objects.all()
    serializer_class = TiendaSerializer
