from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AnularVenta,
    CerrarDia,
    ExportarVentas,
    ListarVentas,
    RegistrarVenta,
    TiendaViewSet,
    VentaPorVoz,
    index,
    pizzeria,
)

router = DefaultRouter()
router.register(r"tiendas", TiendaViewSet)

urlpatterns = [
    path("", index, name="index"),
    path("tienda/", index, name="tienda"),
    path("pizzeria/", pizzeria, name="pizzeria"),
    path("registrar/", RegistrarVenta.as_view(), name="registrar-venta"),
    path("listar/", ListarVentas.as_view(), name="listar-ventas"),
    path("voz/", VentaPorVoz.as_view(), name="venta-por-voz"),
    path("void/", AnularVenta.as_view(), name="anular-venta"),
    path("exportar/", ExportarVentas.as_view(), name="exportar-ventas"),
    path("cerrar-dia/", CerrarDia.as_view(), name="cerrar-dia"),
    path("api-datos/", include(router.urls)),
]
