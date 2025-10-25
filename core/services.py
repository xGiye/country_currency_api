# import requests
# import random
# from django.conf import settings



# COUNTRIES_URL = 'https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies'
# RATES_URL = 'https://open.er-api.com/v6/latest/USD'


# class ExternalAPIError(Exception):
#     pass

# def fetch_countries():
#     try:
#         r = requests.get(COUNTRIES_URL, timeout=settings.EXTERNAL_TIMEOUT)
#         r.raise_for_status()
#         return r.json()
#     except Exception as e:
#         raise ExternalAPIError(f'Could not fetch data from Countries API: {e}')

# def fetch_rates():
#     try:
#         r = requests.get(RATES_URL, timeout=settings.EXTERNAL_TIMEOUT)
#         r.raise_for_status()
#         data = r.json()
#         return data.get('rates', {})
#     except Exception as e:
#         raise ExternalAPIError(f'Could not fetch data from Rates API: {e}')


# def compute_estimated_gdp(population, exchange_rate):
#     if population is None:
#         return None
#     multiplier = random.randint(1000, 2000)
#     if exchange_rate in (None, 0):
#         return None
#     return (population * multiplier) / exchange_rate



# #===================================================================

import requests
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.utils import timezone
from .models import Country, CacheStatus
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ExternalAPIFailureError(Exception):
    """Raised when external API data cannot be fetched."""
    pass


def _get_session_with_retries():
    """Creates a requests session with retry support."""
    s = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    return s


def fetch_countries():
    print("fetch boy")
    """Fetches all countries and currency info from REST Countries API."""
    session = _get_session_with_retries()
    url = "https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies"
    resp = session.get(url, timeout=10)
    if resp.status_code != 200:
        raise ExternalAPIFailureError("REST Countries API")
    return resp.json()


def fetch_exchange_rates():
    """Fetches live exchange rates with USD as base."""
    session = _get_session_with_retries()
    url = "https://open.er-api.com/v6/latest/USD"
    resp = session.get(url, timeout=10)
    if resp.status_code != 200:
        raise ExternalAPIFailureError("Exchange Rate API")
    return resp.json().get("rates", {})


@transaction.atomic
def refresh_country_data():
    """
    Refreshes all country data from the RESTCountries and Exchange Rate APIs.
    Calculates estimated GDP using:
        estimated_gdp = (population × random(1000–2000)) ÷ exchange_rate
    Updates or creates Country records, then updates CacheStatus.
    """

    # Fetch data from external APIs
    countries_data = fetch_countries()
    exchange_rates = fetch_exchange_rates()

    created_count = 0
    updated_count = 0

    for country_data in countries_data:
        # Extract basic fields safely
        name = country_data.get('name')
        if not name:
            continue  # Skip invalid record

        population = country_data.get('population') or 0
        capital = country_data.get('capital') or None
        region = country_data.get('region') or None
        flag_url = country_data.get('flag') or None

        # Extract currency code (from first item if list exists)
        currency_code = None
        currencies = country_data.get('currencies', [])
        if isinstance(currencies, list) and currencies:
            currency_info = currencies[0]
            currency_code = currency_info.get('code')

        # Initialize default values
        exchange_rate = None
        estimated_gdp = None

        # Compute exchange rate and GDP if currency is valid
        if currency_code and currency_code in exchange_rates:
            try:
                rate = Decimal(str(exchange_rates[currency_code]))
                if rate > 0:
                    multiplier = Decimal(random.uniform(1000, 2000))
                    estimated_gdp = (Decimal(population) * multiplier) / rate
                    exchange_rate = rate
            except (InvalidOperation, TypeError, ValueError):
                # Handle invalid numeric conversion
                exchange_rate = None
                estimated_gdp = None
        else:
            # Missing currency or rate info
            exchange_rate = None
            estimated_gdp = Decimal('0')

        # Create or update the country record
        country_obj, created_flag = Country.objects.update_or_create(
            name=name,
            defaults={
                'capital': capital,
                'region': region,
                'population': population,
                'currency_code': currency_code,
                'exchange_rate': exchange_rate,
                'estimated_gdp': estimated_gdp,
                'flag_url': flag_url,
            }
        )

        if created_flag:
            created_count += 1
        else:
            updated_count += 1

    # Update the cache status (clear old one to ensure only one record)
    CacheStatus.objects.all().delete()
    CacheStatus.objects.create(
        last_refreshed_at=timezone.now(),
        total_countries=Country.objects.count()
    )

    return {
        "created": created_count,
        "updated": updated_count,
        "total": Country.objects.count(),
        "timestamp": timezone.now(),
    }