# Country Currency & Exchange API — Django Implementation

A RESTful API built with Django + Django REST Framework, which fetches country data and currency exchange rates from public APIs, computes estimated GDP, and caches the results in a MySQL database.
Includes endpoints for CRUD operations, summary image generation, and refresh tracking.

## Features
- Fetch and cache country data (name, capital, region, population, currency, etc.)
- Compute estimated_gdp = population × random(1000–2000) ÷ exchange_rate
- Filter, sort, and retrieve country data via API endpoints
- Delete individual country records
- Display global cache status (total countries, last refresh time)
- Generate and serve an image summary showing top countries by GDP