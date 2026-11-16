from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
from zoneinfo import ZoneInfo


class WeatherServiceError(Exception):
    """Raised when the upstream weather API fails or returns incomplete data."""


async def fetch_weather_range(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    today = date.today()
    max_forecast_date = today + timedelta(days=15)

    if end_date > max_forecast_date:
        raise WeatherServiceError(
            f"Forecast data is only available up to {max_forecast_date.isoformat()}."
        )

    # Use archive API if start_date is older than 5 days ago; otherwise use forecast API
    use_archive = start_date < (today - timedelta(days=5))
    base_url = (
        "https://archive-api.open-meteo.com/v1/archive"
        if use_archive
        else "https://api.open-meteo.com/v1/forecast"
    )

    params: dict[str, Any] = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "wind_speed_10m_max",
            "uv_index_max",
        ],
        "timezone": "auto",
    }

    if not use_archive:
        params["current"] = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m"]

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(base_url, params=params)
    except httpx.RequestError as exc:
        raise WeatherServiceError("Weather provider is unavailable.") from exc

    if resp.status_code != 200:
        raise WeatherServiceError(
            f"Weather provider error ({resp.status_code}): {resp.text[:200]}"
        )

    data = resp.json()
    daily = data.get("daily", {})
    dates = daily.get("time", [])

    daily_breakdown = []
    for i, day_str in enumerate(dates):
        daily_breakdown.append(
            {
                "date": day_str,
                "temp_max_c": daily.get("temperature_2m_max", [None])[i],
                "temp_min_c": daily.get("temperature_2m_min", [None])[i],
                "precipitation_mm": daily.get("precipitation_sum", [None])[i],
                "wind_max_kmh": daily.get("wind_speed_10m_max", [None])[i],
                "uv_index_max": daily.get("uv_index_max", [None])[i],
            }
        )
    tz_name = data.get("timezone", "UTC")
    try:
        local_now = datetime.now(ZoneInfo(tz_name)).strftime("%I:%M %p (%Z, %Y-%m-%d)")
    except (KeyError, ValueError):
        local_now = datetime.now(timezone.utc).strftime("%H:%M UTC")
    current = data.get("current", {})
    return {
    "source": "open-meteo-archive" if use_archive else "open-meteo-forecast",
    "timezone": tz_name,
    "local_time": local_now,
    "current_temp_c": current.get("temperature_2m"),
    "current_humidity_pct": current.get("relative_humidity_2m"),
    "current_wind_kmh": current.get("wind_speed_10m"),
    "daily": daily_breakdown,
    }