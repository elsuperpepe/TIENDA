from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ListarVentas, RegistrarVenta, TiendaViewSet, VentaPorVoz, index

router = DefaultRouter()
router.register(r"tiendas", TiendaViewSet)

urlpatterns = [
    # 1. Página Web (El Frontend)
    path("tienda/", index),
    # 2. La API (Lo que ya te funciona)
    path("registrar/", RegistrarVenta.as_view()),
    path(
        "api-datos/", include(router.urls)
    ),  # Cambié esto a 'api-datos/' para que no se choque
    path("listar/", ListarVentas.as_view()),
    path("registrar/", RegistrarVenta.as_view(), name="registrar-venta"),
    path("voz/", VentaPorVoz.as_view(), name="venta-por-voz"),
]
