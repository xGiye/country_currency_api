from django.urls import path
from .views import (
    CountryListView,
    CountryDetailView,
    CountryRefreshView,
    CacheStatusView,
    CountryImageView,
)


urlpatterns = [
    path('', CountryListView.as_view(), name='country-list'),                # GET /countries
    path('refresh/', CountryRefreshView.as_view(), name='country-refresh'),  # POST /countries/refresh
    path('image/', CountryImageView.as_view(), name='country-image'),        # GET /countries/image
    path('<str:name>/', CountryDetailView.as_view(), name='country-detail'), # GET/DELETE /countries/:name
]
