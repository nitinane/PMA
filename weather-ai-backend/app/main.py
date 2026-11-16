from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import WeatherRecord
from app.schemas import (
    WeatherQueryCreate,
    WeatherQueryUpdate,
    WeatherRecordResponse,
)
from app.services.advisory import generate_travel_advisory
from app.services.exporter import export_records
from app.services.geocoding import LocationNotFoundError, resolve_location
from app.services.nlp_parser import parse_freeform_query
from app.services.weather import WeatherServiceError, fetch_weather_range
from app.services.youtube import fetch_location_youtube_videos

Base.metadata.create_all(bind=engine)

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="Weather & Travel Intelligence API",
    description=(
        "Backend Engineering Technical Assessment by Nitin Madanala "
        "for Product Manager Accelerator (PM Accelerator)."
    ),
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def serve_chat_ui():
    return FileResponse(STATIC_DIR / "index.html")


@app.post(
    "/chat-query",
    response_model=WeatherRecordResponse,
    status_code=201,
    tags=["Weather CRUD"],
)
async def create_weather_from_freeform_text(
    payload: dict[str, str], db: Session = Depends(get_db)
):
    raw_text = payload.get("query", "").strip()
    if not raw_text:
        raise HTTPException(status_code=422, detail="Query text cannot be empty.")

    parsed = parse_freeform_query(raw_text)
    structured = WeatherQueryCreate(
        location=parsed.location,
        start_date=parsed.start_date,
        end_date=parsed.end_date,
    )
    return await create_weather_query(structured, db)


@app.get("/about", tags=["Info"])
def about_project():
    return {
        "developer": "Nitin Madanala",
        "role_track": "Backend Engineering (Tech Assessment #2)",
        "organization": "Product Manager Accelerator (PM Accelerator)",
        "pm_accelerator_description": (
            "Product Manager Accelerator (PM Accelerator), founded by Dr. Nancy Li, "
            "is a career coaching and hands-on Product Management training organization "
            "that helps aspiring and experienced professionals build real-world products, "
            "develop product portfolios, and land Product Manager roles."
        ),
    }


@app.post(
    "/weather-queries",
    response_model=WeatherRecordResponse,
    status_code=201,
    tags=["Weather CRUD"],
)
async def create_weather_query(
    payload: WeatherQueryCreate, db: Session = Depends(get_db)
):
    try:
        loc = await resolve_location(payload.location)
    except LocationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    lat, lon = loc["latitude"], loc["longitude"]
    resolved_name = loc["resolved_name"]
    maps_url = loc.get(
        "google_maps_url", f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
    )

    try:
        weather_data = await fetch_weather_range(
            lat, lon, payload.start_date, payload.end_date
        )
    except WeatherServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    # Attach location-specific YouTube search links (Requirement 2.2)
    videos = await fetch_location_youtube_videos(resolved_name, loc.get("country"))
    weather_data["youtube_videos"] = videos
    weather_data["youtube_travel_search_url"] = (
        videos[0]["url"]
        if videos
        else f"https://www.youtube.com/results?search_query={resolved_name.replace(' ', '+')}+travel+guide"
    )

    advisory = generate_travel_advisory(resolved_name, weather_data)

    record = WeatherRecord(
        raw_location_input=payload.location,
        resolved_location=resolved_name,
        country=loc.get("country"),
        latitude=lat,
        longitude=lon,
        start_date=payload.start_date,
        end_date=payload.end_date,
        current_temp_c=weather_data.get("current_temp_c"),
        weather_summary=weather_data,
        travel_advisory=advisory,
        google_maps_url=maps_url,
        user_notes=payload.user_notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get(
    "/weather-queries",
    response_model=list[WeatherRecordResponse],
    tags=["Weather CRUD"],
)
def read_all_weather_queries(db: Session = Depends(get_db)):
    return db.query(WeatherRecord).order_by(WeatherRecord.id.desc()).all()


@app.get("/weather-queries/export", tags=["Data Export"])
def export_weather_queries(
    format: str = Query("json", pattern="^(json|csv|markdown)$"),
    db: Session = Depends(get_db),
):
    records = db.query(WeatherRecord).order_by(WeatherRecord.id.asc()).all()
    content, media_type, filename = export_records(records, format)
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get(
    "/weather-queries/{record_id}",
    response_model=WeatherRecordResponse,
    tags=["Weather CRUD"],
)
def read_weather_query(record_id: int, db: Session = Depends(get_db)):
    record = db.query(WeatherRecord).filter(WeatherRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Record {record_id} not found.")
    return record


@app.put(
    "/weather-queries/{record_id}",
    response_model=WeatherRecordResponse,
    tags=["Weather CRUD"],
)
async def update_weather_query(
    record_id: int, payload: WeatherQueryUpdate, db: Session = Depends(get_db)
):
    record = db.query(WeatherRecord).filter(WeatherRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Record {record_id} not found.")

    new_start = payload.start_date or record.start_date
    new_end = payload.end_date or record.end_date

    if new_start > new_end:
        raise HTTPException(
            status_code=422, detail="start_date cannot be after end_date."
        )
    if (new_end - new_start).days > 14:
        raise HTTPException(
            status_code=422, detail="Date range cannot exceed 14 days."
        )

    location_changed = (
        payload.location is not None and payload.location != record.raw_location_input
    )
    dates_changed = (
        new_start != record.start_date or new_end != record.end_date
    )

    if location_changed:
        try:
            loc = await resolve_location(payload.location)
        except LocationNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

        record.raw_location_input = payload.location
        record.resolved_location = loc["resolved_name"]
        record.country = loc.get("country")
        record.latitude = loc["latitude"]
        record.longitude = loc["longitude"]
        record.google_maps_url = loc.get(
            "google_maps_url",
            f"https://www.google.com/maps/search/?api=1&query={record.latitude},{record.longitude}",
        )

    if location_changed or dates_changed:
        try:
            weather_data = await fetch_weather_range(
                record.latitude, record.longitude, new_start, new_end
            )
        except WeatherServiceError as exc:
            raise HTTPException(status_code=502, detail=str(exc))

        # Refresh YouTube videos if location changed, otherwise reuse existing ones
        if location_changed:
            videos = await fetch_location_youtube_videos(
                record.resolved_location, record.country
            )
        else:
            videos = (record.weather_summary or {}).get("youtube_videos", [])

        weather_data["youtube_videos"] = videos
        weather_data["youtube_travel_search_url"] = (
            videos[0]["url"]
            if videos
            else f"https://www.youtube.com/results?search_query={record.resolved_location.replace(' ', '+')}+travel+guide"
        )

        record.start_date = new_start
        record.end_date = new_end
        record.current_temp_c = weather_data.get("current_temp_c")
        record.weather_summary = weather_data
        record.travel_advisory = generate_travel_advisory(
            record.resolved_location, weather_data
        )

    if payload.user_notes is not None:
        record.user_notes = payload.user_notes

    record.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    return record


@app.delete("/weather-queries/{record_id}", tags=["Weather CRUD"])
def delete_weather_query(record_id: int, db: Session = Depends(get_db)):
    record = db.query(WeatherRecord).filter(WeatherRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Record {record_id} not found.")
    db.delete(record)
    db.commit()
    return {"deleted_id": record_id, "status": "deleted"}