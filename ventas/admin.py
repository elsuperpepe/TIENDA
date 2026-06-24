from django.contrib import admin

from .models import ItemVenta, Venta

# Esto registra tus modelos en el panel de control
admin.site.register(Venta)
admin.site.register(ItemVenta)
