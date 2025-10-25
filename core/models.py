from django.db import models

# Create your models here.
class Country(models.Model):
    """Stores information about a single country."""
    name = models.CharField(max_length=100, unique=True)
    capital = models.CharField(max_length=100, null=True, blank=True)
    region = models.CharField(max_length=50, null=True, blank=True)
    population = models.BigIntegerField()

    currency_code = models.CharField(max_length=10, null=True, blank=True)
    exchange_rate = models.DecimalField(max_digits=20, decimal_places=6, blank=True, null=True)
    estimated_gdp = models.DecimalField(max_digits=30, decimal_places=2, blank=True, null=True, db_index=True)

    flag_url = models.URLField(max_length=255, blank=True, null=True)
    last_refreshed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name
    
class CacheStatus(models.Model):
    """Tracks the last time country data was refreshed."""
    last_refreshed_at = models.DateTimeField(null=True, blank=True)
    total_countries = models.IntegerField(default=0)

    def __str__(self):
        return f"CacheStatus (last refreshed: {self.last_refreshed_at})"