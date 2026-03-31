"""
External API tools used by the Claude agent.
All free/open APIs — no API key required.
"""
import httpx
import json
from typing import Optional

HEADERS = {"User-Agent": "ZoneAI/1.0 (portfolio project)"}


async def geocode_address(address: str) -> dict:
    """Geocode an address using Nominatim (OpenStreetMap)."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1, "countrycodes": "fr"},
            headers=HEADERS,
            timeout=10,
        )
        results = r.json()
        if not results:
            return {"error": f"Adresse introuvable : {address}"}

        result = results[0]
        return {
            "lat": float(result["lat"]),
            "lon": float(result["lon"]),
            "display_name": result["display_name"],
            "address": result.get("address", {}),
        }


async def get_competitors(lat: float, lon: float, radius_m: int, category: str) -> dict:
    """
    Fetch nearby competitors/POIs from OpenStreetMap via Overpass API.
    category: restaurant | pharmacy | supermarket | bank | cafe | gym | school
    """
    TAG_MAP = {
        "restaurant": 'amenity"="restaurant',
        "pharmacy": 'amenity"="pharmacy',
        "supermarket": 'shop"="supermarket',
        "bank": 'amenity"="bank',
        "cafe": 'amenity"="cafe',
        "gym": 'leisure"="fitness_centre',
        "school": 'amenity"="school',
        "hotel": 'tourism"="hotel',
        "bakery": 'shop"="bakery',
    }
    tag = TAG_MAP.get(category, f'amenity"="{category}')
    query = f"""
    [out:json][timeout:15];
    (
      node["{tag}](around:{radius_m},{lat},{lon});
      way["{tag}](around:{radius_m},{lat},{lon});
    );
    out center {50};
    """
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query},
            timeout=20,
        )
        data = r.json()

    elements = data.get("elements", [])
    pois = []
    for el in elements[:20]:
        tags = el.get("tags", {})
        center = el.get("center", el)
        pois.append({
            "name": tags.get("name", "Sans nom"),
            "lat": center.get("lat"),
            "lon": center.get("lon"),
            "brand": tags.get("brand", ""),
            "opening_hours": tags.get("opening_hours", ""),
        })

    return {
        "category": category,
        "radius_m": radius_m,
        "count": len(elements),
        "top_results": pois[:10],
    }


async def get_commune_info(lat: float, lon: float) -> dict:
    """Get French commune info (population, INSEE code) from api.gouv.fr."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://geo.api.gouv.fr/communes",
            params={"lat": lat, "lon": lon, "fields": "nom,code,population,codesPostaux,surface", "format": "json"},
            timeout=10,
        )
        results = r.json()
        if not results:
            return {"error": "Commune introuvable"}

        commune = results[0]
        surface_km2 = commune.get("surface", 0) / 100  # hectares -> km2
        population = commune.get("population", 0)
        density = round(population / surface_km2, 0) if surface_km2 > 0 else 0

        return {
            "commune": commune.get("nom"),
            "code_insee": commune.get("code"),
            "codes_postaux": commune.get("codesPostaux", []),
            "population": population,
            "surface_km2": round(surface_km2, 2),
            "density_per_km2": density,
        }


async def get_isochrone_estimate(lat: float, lon: float, minutes: int) -> dict:
    """
    Estimate catchment zone radius from travel time.
    Simple approximation: walking ~5km/h, driving ~30km/h in urban area.
    """
    walk_radius_m = int((minutes / 60) * 5000)
    drive_radius_m = int((minutes / 60) * 30000)
    return {
        "travel_time_minutes": minutes,
        "walk_radius_m": walk_radius_m,
        "drive_radius_m": drive_radius_m,
        "note": "Estimation basée sur vitesse moyenne urbaine (piéton 5km/h, voiture 30km/h)"
    }
