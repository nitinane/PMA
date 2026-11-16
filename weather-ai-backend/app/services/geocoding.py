import re
import httpx


class LocationNotFoundError(Exception):
    """Raised when user location input cannot be resolved to valid coordinates."""


GPS_PATTERN = re.compile(
    r"^\s*([+-]?\d+(?:\.\d+)?)\s*[,\s]\s*([+-]?\d+(?:\.\d+)?)\s*$"
)


def _build_maps_url(lat: float, lon: float) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"


async def _reverse_geocode(latitude: float, longitude: float) -> dict[str, str]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={
                    "lat": latitude,
                    "lon": longitude,
                    "format": "json",
                    "zoom": 18,
                    "addressdetails": 1,
                },
                headers={"User-Agent": "PM-Accelerator-Weather-App/1.0"},
            )
        if response.status_code != 200:
            return {}

        address = response.json().get("address", {})
        locality = next(
            (
                address.get(key)
                for key in (
                    "neighbourhood",
                    "suburb",
                    "city_district",
                    "city",
                    "town",
                    "village",
                    "municipality",
                )
                if address.get(key)
            ),
            None,
        )
        region = address.get("state") or address.get("state_district")
        country = address.get("country")
        name = ", ".join(part for part in (locality, region, country) if part)
        return {"resolved_name": name, "country": country or ""}
    except (httpx.RequestError, ValueError, TypeError):
        return {}


def _build_candidate_queries(raw: str) -> list[str]:
    """Generates progressively broader fuzzy candidates for multi-word places."""
    cleaned = re.sub(r"\s+", " ", raw).strip(" ,.-")
    candidates = [cleaned]

    words = [w.strip(",") for w in cleaned.split(" ") if w.strip(",")]
    if len(words) >= 2:
        # Try comma-separated ("nanakramguda, hyderabad")
        comma_form = ", ".join(words)
        if comma_form not in candidates:
            candidates.append(comma_form)
        # Try individual significant tokens (e.g., neighborhood first, then city)
        for w in words:
            if len(w) >= 3 and w not in candidates:
                candidates.append(w)

    return candidates


async def resolve_location(raw_input: str) -> dict:
    cleaned = raw_input.strip()

    # 1. Raw GPS coordinates ("17.3616, 78.4747" or "17.3616 78.4747")
    gps_match = GPS_PATTERN.match(cleaned)
    if gps_match:
        lat = float(gps_match.group(1))
        lon = float(gps_match.group(2))
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            raise LocationNotFoundError(
                f"GPS coordinates ({lat}, {lon}) are out of valid Earth bounds."
            )
        nearby_place = await _reverse_geocode(lat, lon)
        return {
            "resolved_name": nearby_place.get(
                "resolved_name", f"GPS ({lat:.4f}, {lon:.4f})"
            ),
            "country": nearby_place.get("country") or None,
            "latitude": lat,
            "longitude": lon,
            "google_maps_url": _build_maps_url(lat, lon),
        }

    candidates = _build_candidate_queries(cleaned)

    async with httpx.AsyncClient(timeout=10.0) as client:
        for query in candidates:
            # 2. Try OpenStreetMap Nominatim first for neighborhoods, landmarks & postal codes
            nom_resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "json", "limit": 1, "addressdetails": 1},
                headers={"User-Agent": "PM-Accelerator-Weather-Assessment/1.0"},
            )
            if nom_resp.status_code == 200 and nom_resp.json():
                top = nom_resp.json()[0]
                lat, lon = float(top["lat"]), float(top["lon"])
                addr = top.get("address", {})
                short_parts = [
                    addr.get("suburb")
                    or addr.get("neighbourhood")
                    or addr.get("city_district")
                    or top.get("name"),
                    addr.get("city") or addr.get("town") or addr.get("state"),
                ]
                display_name = ", ".join([p for p in short_parts if p]) or top.get(
                    "display_name", query
                )[:120]
                return {
                    "resolved_name": display_name,
                    "country": addr.get("country"),
                    "latitude": lat,
                    "longitude": lon,
                    "google_maps_url": _build_maps_url(lat, lon),
                }

            # 3. Try Open-Meteo Geocoding API (handles fuzzy spelling for cities/towns)
            om_resp = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": query, "count": 1, "language": "en", "format": "json"},
            )
            if om_resp.status_code == 200:
                results = om_resp.json().get("results")
                if results:
                    top = results[0]
                    lat, lon = top["latitude"], top["longitude"]
                    admin = top.get("admin1", "")
                    display_name = f"{top['name']}, {admin}".strip(", ")
                    return {
                        "resolved_name": display_name,
                        "country": top.get("country"),
                        "latitude": lat,
                        "longitude": lon,
                        "google_maps_url": _build_maps_url(lat, lon),
                    }

    raise LocationNotFoundError(
        f"Could not find any real-world location matching '{raw_input}'."
    )