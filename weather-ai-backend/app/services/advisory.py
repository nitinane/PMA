from typing import Any


def generate_travel_advisory(
    location_name: str, weather_data: dict[str, Any]
) -> str:
    daily = weather_data.get("daily") or []
    current_temp = weather_data.get("current_temp_c")
    current_wind = weather_data.get("current_wind_kmh")
    current_humidity = weather_data.get("current_humidity_pct")

    recommendations: list[str] = []
    if daily:
        lows = [day["temp_min_c"] for day in daily if day.get("temp_min_c") is not None]
        highs = [day["temp_max_c"] for day in daily if day.get("temp_max_c") is not None]
        rain = [
            day["precipitation_mm"]
            for day in daily
            if day.get("precipitation_mm") is not None
        ]
        uv = [day["uv_index_max"] for day in daily if day.get("uv_index_max") is not None]
        wind = [day["wind_max_kmh"] for day in daily if day.get("wind_max_kmh") is not None]

        if lows and highs and max(highs) - min(lows) >= 8:
            recommendations.append(
                f"Temperatures range from {min(lows):g}°C to {max(highs):g}°C; "
                "light layers will help throughout the day."
            )
        if rain and max(rain) > 1:
            recommendations.append(
                f"Rainfall may reach {max(rain):g} mm; carry an umbrella or rain jacket."
            )
        if uv and max(uv) >= 6:
            recommendations.append(
                f"UV levels reach {max(uv):g}; use sunscreen, a hat, and shade outdoors."
            )
        if wind and max(wind) >= 30:
            recommendations.append(
                f"Wind gusts may reach {max(wind):g} km/h; take care near exposed areas."
            )

    if not recommendations:
        recommendations.append("Conditions look broadly suitable for normal outdoor plans.")
    if current_temp is not None and current_humidity is not None and current_humidity >= 80:
        recommendations.append(
            f"Current humidity is {current_humidity:g}%; allow extra time for comfort outdoors."
        )
    if current_wind is not None and current_wind >= 30:
        recommendations.append(
            f"Current wind is {current_wind:g} km/h; secure loose belongings outdoors."
        )

    return "\n".join(
        f"{index}. {recommendation}"
        for index, recommendation in enumerate(recommendations[:3], start=1)
    )
