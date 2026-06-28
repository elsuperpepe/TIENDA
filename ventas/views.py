import csv

from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from inventario.models import Tienda
from inventario.serializers import TiendaSerializer

from .models import Venta
from .serializers import VentaEntradaSerializer
from .services import VentaService, VozParser


class TiendaViewSet(viewsets.ModelViewSet):
    queryset = Tienda.objects.all()
    serializer_class = TiendaSerializer


def index(request):
    return render(request, "index.html")


def pizzeria(request):
    return render(request, "pizzas.html")


class RegistrarVenta(APIView):
    """
    Recibe los items del carrito y delega TODO al VentaService.
    El view no tiene lógica de negocio — solo valida entrada y formatea salida.
    """

    def post(self, request):
        serializer = VentaEntradaSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        datos = serializer.validated_data
        # El serializer resuelve tienda_id a una instancia — sacamos el id entero
        tienda_id = datos["tienda_id"].id
        items_data = [
            {
                "producto_id": item["producto_id"].id,
                "cantidad": item["cantidad"],
                "nota": item.get("nota", ""),
            }
            for item in datos["items"]
        ]

        try:
            venta = VentaService.registrar(tienda_id, items_data)
            return Response(
                {
                    "mensaje": "Venta realizada con éxito",
                    "venta_id": venta.id,
                    "total": float(venta.total),
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": "Error inesperado al procesar la venta", "detalle": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AnularVenta(APIView):
    def post(self, request):
        venta_id = request.data.get("venta_id")
        if not venta_id:
            return Response(
                {"error": "Se requiere venta_id"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            venta = VentaService.void(venta_id)
            return Response(
                {
                    "mensaje": f"Venta #{venta.id} anulada correctamente",
                    "total_devuelto": float(venta.total),
                }
            )
        except Venta.DoesNotExist:
            return Response(
                {"error": "Venta no encontrada"}, status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": "Error interno", "detalle": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CerrarDia(APIView):
    def post(self, request):
        ventas_activas = Venta.objects.filter(cancelada=False, cerrada=False)
        # Guardar el count ANTES del update — después del update el queryset devuelve 0
        total_ventas = ventas_activas.count()

        if total_ventas == 0:
            return Response(
                {"error": "No hay ventas activas para cerrar."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            ventas_activas.update(cerrada=True)

        return Response(
            {
                "mensaje": f"Día cerrado correctamente. {total_ventas} venta(s) cerradas.",
                "ventas_cerradas": total_ventas,
            },
            status=status.HTTP_200_OK,
        )


class VentaPorVoz(APIView):
    def post(self, request):
        texto = request.data.get("texto", "").strip()
        tienda_id = request.data.get("tienda_id", 1)

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
        ventas = Venta.objects.filter(cancelada=False, cerrada=False)
        lista = [{"id": v.id, "total": float(v.total)} for v in ventas]
        total_general = ventas.aggregate(Sum("total"))["total__sum"] or 0
        return Response({"ventas": lista, "total_general": float(total_general)})


class ExportarVentas(APIView):
    def get(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="ventas.csv"'
        writer = csv.writer(response)
        writer.writerow(
            ["ID", "Fecha", "Tienda", "Total", "Cancelada", "Cerrada", "Items"]
        )

        for venta in Venta.objects.all().prefetch_related("items__producto"):
            items_texto = ", ".join(
                [
                    f"{i.cantidad}x {i.producto.nombre}"
                    + (f" ({i.nota})" if i.nota else "")
                    for i in venta.items.all()
                ]
            )
            writer.writerow(
                [
                    venta.id,
                    venta.fecha.strftime("%Y-%m-%d %H:%M"),
                    venta.tienda.nombre,
                    venta.total,
                    venta.cancelada,
                    venta.cerrada,
                    items_texto,
                ]
            )

        return response
