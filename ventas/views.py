from django.db import transaction
from django.db.models import Sum
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from inventario.models import Producto, Tienda
from inventario.serializers import TiendaSerializer

from .models import ItemVenta, Venta
from .serializers import VentaEntradaSerializer
from .services import VentaService, VozParser


def index(request):
    return render(request, "index.html")


class TiendaViewSet(viewsets.ModelViewSet):
    queryset = Tienda.objects.all()
    serializer_class = TiendaSerializer


@method_decorator(csrf_exempt, name="dispatch")
class RegistrarVenta(APIView):
    def post(self, request):
        # Validar con serializer
        serializer = VentaEntradaSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        datos = serializer.validated_data
        tienda = datos["tienda_id"]
        items_data = datos["items"]

        try:
            with transaction.atomic():
                ids_productos = [item["producto_id"].id for item in items_data]
                productos = (
                    Producto.objects.select_for_update()
                    .filter(id__in=ids_productos)
                    .order_by("id")
                )

                # Validar stock solo para productos físicos
                for producto, item in zip(productos, items_data):
                    if not producto.es_servicio:
                        if producto.stock < item["cantidad"]:
                            return Response(
                                {
                                    "error": f"Stock insuficiente para '{producto.nombre}'",
                                    "disponible": producto.stock,
                                    "solicitado": item["cantidad"],
                                },
                                status=status.HTTP_400_BAD_REQUEST,
                            )

                # Crear venta
                venta = Venta.objects.create(tienda=tienda, total=0)

                total_venta = 0
                for producto, item in zip(productos, items_data):
                    cantidad = item["cantidad"]
                    precio_unitario = producto.precio
                    subtotal = precio_unitario * cantidad

                    ItemVenta.objects.create(
                        venta=venta,
                        producto=producto,
                        cantidad=cantidad,
                        precio_unitario=precio_unitario,
                    )

                    if not producto.es_servicio:
                        producto.stock -= cantidad
                        producto.save()

                    total_venta += subtotal

                venta.total = total_venta
                venta.save()

            return Response(
                {
                    "mensaje": "Venta realizada con éxito",
                    "venta_id": venta.id,
                    "total": float(total_venta),
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"error": "Error inesperado al procesar la venta", "detalle": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VentaPorVoz(APIView):
    def post(self, request):
        texto = request.data.get("texto", "")
        tienda_id = request.data.get("tienda_id", 1)  # por defecto la tienda 1

        if not texto:
            return Response(
                {"error": "Envía un texto con tu pedido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            items = VozParser.parse(texto)
            venta = VentaService.registrar(tienda_id, items)
            return Response(
                {
                    "mensaje": "Venta por voz exitosa",
                    "texto_recibido": texto,
                    "venta_id": venta.id,
                    "total": float(venta.total),
                    "items_detectados": items,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": "Error interno", "detalle": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ListarVentas(APIView):
    def get(self, request):
        ventas = Venta.objects.all()
        lista = [{"id": v.id, "total": float(v.total)} for v in ventas]
        total_general = ventas.aggregate(Sum("total"))["total__sum"] or 0
        return Response({"ventas": lista, "total_general": total_general})
