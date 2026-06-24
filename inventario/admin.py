from django.contrib import admin

from .models import Producto, Tienda

admin.site.register(Tienda)
admin.site.register(Producto)
