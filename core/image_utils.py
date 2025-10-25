from PIL import Image, ImageDraw, ImageFont
from .models import Country, CacheStatus
from datetime import datetime
import os


def generate_summary_image():
    """Generates a simple PNG summary of current country stats."""
    total_countries = Country.objects.count()
    top_5 = Country.objects.order_by('-estimated_gdp')[:5].values('name', 'estimated_gdp')

    try:
        status = CacheStatus.objects.first()
        last_refresh = status.last_refreshed_at if status else None
    except Exception:
        last_refresh = None

    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    y = 50
    draw.text((50, y), f"🌍 Country Summary", fill=(0, 0, 0), font=font)
    y += 40
    draw.text((50, y), f"Total Countries: {total_countries}", fill=(0, 0, 0), font=font)
    y += 40
    draw.text((50, y), f"Last Refresh: {last_refresh.strftime('%Y-%m-%d %H:%M:%S') if last_refresh else 'N/A'}",
              fill=(0, 0, 0), font=font)

    y += 60
    draw.text((50, y), "Top 5 Countries by Estimated GDP:", fill=(0, 0, 0), font=font)
    y += 30

    for i, c in enumerate(top_5, 1):
        line = f"{i}. {c['name']} - ${float(c['estimated_gdp']):,.2f}"
        draw.text((70, y), line, fill=(0, 0, 0), font=font)
        y += 30

    os.makedirs('cache', exist_ok=True)
    img.save('cache/summary.png')


# Image Generation
# When /countries/refresh runs:
#   After saving countries in the database, generate an image (e.g., cache/summary.png) containing:

#       Total number of countries
#       Top 5 countries by estimated GDP
#       Timestamp of last refresh

# Save the generated image on disk at cache/summary.png.

# Add a new endpoint:
# GET /countries/image → Serve the generated summary image
# If no image exists, return:
# { "error": "Summary image not found" }