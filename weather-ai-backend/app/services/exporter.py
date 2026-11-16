import csv
import io
import json
from app.models import WeatherRecord


def export_records(records: list[WeatherRecord], fmt: str) -> tuple[str, str, str]:
    """Returns (content_string, media_type, filename)."""
    fmt = fmt.lower()

    if fmt == "json":
        payload = [
            {
                "id": r.id,
                "raw_location_input": r.raw_location_input,
                "resolved_location": r.resolved_location,
                "country": r.country,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "start_date": r.start_date.isoformat(),
                "end_date": r.end_date.isoformat(),
                "current_temp_c": r.current_temp_c,
                "travel_advisory": r.travel_advisory,
                "google_maps_url": r.google_maps_url,
                "user_notes": r.user_notes,
                "weather_summary": r.weather_summary,
            }
            for r in records
        ]
        return (
            json.dumps(payload, indent=2),
            "application/json",
            "weather_records.json",
        )

    if fmt == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "id",
                "raw_location_input",
                "resolved_location",
                "country",
                "latitude",
                "longitude",
                "start_date",
                "end_date",
                "current_temp_c",
                "travel_advisory",
                "google_maps_url",
                "user_notes",
            ]
        )
        for r in records:
            writer.writerow(
                [
                    r.id,
                    r.raw_location_input,
                    r.resolved_location,
                    r.country,
                    r.latitude,
                    r.longitude,
                    r.start_date.isoformat(),
                    r.end_date.isoformat(),
                    r.current_temp_c,
                    r.travel_advisory,
                    r.google_maps_url,
                    r.user_notes or "",
                ]
            )
        return buffer.getvalue(), "text/csv", "weather_records.csv"

    if fmt == "markdown":
        lines = [
            "# Weather & Travel Advisory Records",
            "",
            "| ID | Location | Country | Dates | Current Temp (°C) | Google Maps | Travel Advisory |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in records:
            temp = f"{r.current_temp_c}°C" if r.current_temp_c is not None else "Historical"
            advisory_clean = r.travel_advisory.replace("|", "/").replace("\n", " ")
            lines.append(
                f"| {r.id} | {r.resolved_location} | {r.country or '-'} | "
                f"{r.start_date} to {r.end_date} | {temp} | [Map]({r.google_maps_url}) | {advisory_clean} |"
            )
        return "\n".join(lines), "text/markdown", "weather_records.md"

    raise ValueError("Unsupported format. Choose from: json, csv, markdown.")