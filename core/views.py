# from django.shortcuts import render

# # Create your views here.
# from rest_framework.decorators import api_view
# from rest_framework.response import Response
# from rest_framework import status
# from .models import Country
# from .serializers import CountrySerializer
# from django.shortcuts import get_object_or_404
# from django.conf import settings
# from django.http import FileResponse
# import os
# from django.utils import timezone
# from .services import fetch_countries, fetch_rates, ExternalAPIError, compute_estimated_gdp
# from django.db import transaction
# from .image_gen import generate_summary_image


# @api_view(['POST'])
# def refresh_view(request):
#     # Similar logic as management command, but via HTTP
#     try:
#         countries = fetch_countries()
#         rates = fetch_rates()
#     except ExternalAPIError:
#         return Response({'error': 'External data source unavailable', 'details': 'Could not fetch data from external API'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


#     now = timezone.now()
#     try:
#         with transaction.atomic():
#             for c in countries:
#                 name = c.get('name')
#                 capital = c.get('capital')
#                 region = c.get('region')
#                 population = c.get('population') or 0
#                 flag = c.get('flag')


#                 currency_code = None
#                 exchange_rate = None
#                 estimated_gdp = None


#                 currencies = c.get('currencies') or []
#                 if currencies:
#                     currency_code = currencies[0].get('code')
#                     if currency_code and currency_code in rates:
#                         exchange_rate = float(rates[currency_code])
#                         estimated_gdp = compute_estimated_gdp(population, exchange_rate)
#                     else:
#                         exchange_rate = None
#                         estimated_gdp = None
#                 else:
#                     currency_code = None
#                     exchange_rate = None
#                     estimated_gdp = 0


#                 obj = Country.objects.filter(name__iexact=name).first()
#                 if obj:
#                     obj.capital = capital
#                     obj.region = region
#                     obj.population = population
#                     obj.currency_code = currency_code
#                     obj.exchange_rate = exchange_rate
#                     obj.estimated_gdp = estimated_gdp
#                     obj.flag_url = flag
#                     obj.last_refreshed_at = now
#                     obj.save()
#                 else:
#                     Country.objects.create(
#                         name=name,
#                         capital=capital,
#                         region=region,
#                         population=population,
#                         currency_code=currency_code,
#                         exchange_rate=exchange_rate,
#                         estimated_gdp=estimated_gdp,
#                         flag_url=flag,
#                         last_refreshed_at=now
#                     )
#     except Exception as e:
#         return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#     # generate summary image
#     total = Country.objects.count()
#     top5 = Country.objects.filter(estimated_gdp__isnull=False).order_by('-estimated_gdp')[:5]
#     generate_summary_image(total, top5, now, settings.CACHE_IMAGE_PATH)


#     return Response({'success': True, 'total_countries': total, 'last_refreshed_at': now.isoformat()})


# @api_view(['GET'])
# def countries_list(request):
#     region = request.query_params.get('region')
#     currency = request.query_params.get('currency')
#     sort = request.query_params.get('sort')


#     qs = Country.objects.all()
#     if region:
#         qs = qs.filter(region=region)
#     if currency:
#         qs = qs.filter(currency_code=currency)
#     if sort == 'gdp_desc':
#         qs = qs.order_by('-estimated_gdp')
#     if sort == 'gdp_asc':
#         qs = qs.order_by('estimated_gdp')


#     serializer = CountrySerializer(qs, many=True)
#     return Response(serializer.data)


# @api_view(['GET'])
# def country_detail(request, name):
#     country = Country.objects.filter(name__iexact=name).first()
#     if not country:
#         return Response({'error': 'Country not found'}, status=status.HTTP_404_NOT_FOUND)
#     serializer = CountrySerializer(country)
#     return Response(serializer.data)


# @api_view(['DELETE'])
# def country_delete(request, name):
#     country = Country.objects.filter(name__iexact=name).first()
#     if not country:
#         return Response({'error': 'Country not found'}, status=status.HTTP_404_NOT_FOUND)
#     country.delete()
#     return Response({'success': True})


# @api_view(['GET'])
# def status_view(request):
#     total = Country.objects.count()
#     last = Country.objects.order_by('-last_refreshed_at').first()
#     return Response({'total_countries': total, 'last_refreshed_at': last.last_refreshed_at.isoformat() if last and last.last_refreshed_at else None})


# @api_view(['GET'])
# def image_view(request):
#     p = settings.CACHE_IMAGE_PATH
#     if not os.path.exists(p):
#         return Response({'error': 'Summary image not found'}, status=status.HTTP_404_NOT_FOUND)
#     return FileResponse(open(p, 'rb'), content_type='image/png')


from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Country, CacheStatus
from .serializers import CountrySerializer, CacheStatusSerializer
from .services import refresh_country_data, ExternalAPIFailureError
from .image_utils import generate_summary_image
import os


# -----------------------------------------------------------
# GET /countries → list all countries (with filter/sort)
# -----------------------------------------------------------
class CountryListView(generics.ListAPIView):
    serializer_class = CountrySerializer

    def get_queryset(self):
        queryset = Country.objects.all()

        # Filtering
        region = self.request.query_params.get('region')
        currency = self.request.query_params.get('currency')
        if region:
            queryset = queryset.filter(region__iexact=region)
        if currency:
            queryset = queryset.filter(currency_code__iexact=currency)

        # Sorting (?sort=gdp_desc, ?sort=population_asc, ?sort=name_desc)
        sort_param = self.request.query_params.get('sort')
        if sort_param:
            valid_fields = {
                'gdp': 'estimated_gdp',
                'population': 'population',
                'name': 'name'
            }
            try:
                field, direction = sort_param.split('_')
                if field in valid_fields:
                    sort_field = valid_fields[field]
                    if direction == 'desc':
                        sort_field = f'-{sort_field}'
                    queryset = queryset.order_by(sort_field)
            except ValueError:
                pass

        return queryset


# -----------------------------------------------------------
# GET /countries/:name → retrieve a country by name
# DELETE /countries/:name → delete a country
# -----------------------------------------------------------
class CountryDetailView(APIView):
    def get(self, request, name):
        country = get_object_or_404(Country, name__iexact=name)
        serializer = CountrySerializer(country)
        return Response(serializer.data)

    def delete(self, request, name):
        country = get_object_or_404(Country, name__iexact=name)
        country.delete()
        return Response({"message": f"{name} deleted successfully."}, status=status.HTTP_204_NO_CONTENT)


# -----------------------------------------------------------
# POST /countries/refresh → refresh all data
# -----------------------------------------------------------
class CountryRefreshView(APIView):
    def post(self, request):
        try:
            result = refresh_country_data()
            generate_summary_image()
            return Response(
                {"message": "Data refreshed successfully", "result": result},
                status=status.HTTP_201_CREATED
            )
        except ExternalAPIFailureError as e:
            return Response(
                {"error": "External API failure", "details": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            return Response(
                {"error": "Internal server error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# -----------------------------------------------------------
# GET /status → show cache summary
# -----------------------------------------------------------
class CacheStatusView(APIView):
    def get(self, request):
        status_obj = CacheStatus.objects.first()
        if not status_obj:
            return Response(
                {"message": "No cache record found."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = CacheStatusSerializer(status_obj)
        return Response(serializer.data, status=status.HTTP_200_OK)


# -----------------------------------------------------------
# GET /countries/image → serve summary image
# -----------------------------------------------------------
class CountryImageView(APIView):
    def get(self, request):
        image_path = 'cache/summary.png'
        if os.path.exists(image_path):
            return FileResponse(open(image_path, 'rb'), content_type='image/png')
        return Response(
            {"error": "Summary image not found"},
            status=status.HTTP_404_NOT_FOUND
        )
