# inventario/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ProductoViewSet, TiendaViewSet

router = DefaultRouter()
router.register(r"productos", ProductoViewSet)
router.register(r"tiendas", TiendaViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
