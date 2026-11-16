# Weather Assistant

Weather and travel planning application built for the Product Manager Accelerator
technical assessment.

**Developer:** Nitin Madanala  
**Track:** Backend Engineering

Product Manager Accelerator (PM Accelerator), founded by Dr. Nancy Li, is a
career coaching and hands-on Product Management training organization that
helps aspiring and experienced professionals build real-world products,
develop product portfolios, and land Product Manager roles.

## What the application does

- Accepts cities, towns, landmarks, postal codes, and latitude/longitude.
- Uses the browser's current location when permission is granted.
- Retrieves real weather data from Open-Meteo.
- Shows a five-day default forecast and supports custom date ranges up to 14 days.
- Resolves locations through OpenStreetMap Nominatim and Open-Meteo Geocoding.
- Stores weather requests and travel notes in SQLite.
- Provides create, read, update, and delete operations.
- Adds Google Maps links and YouTube travel-search links for resolved locations.
- Generates travel guidance from the returned weather measurements.
- Exports saved records as JSON, CSV, or Markdown.

## Requirements

- Python 3.10 or newer
- Internet access for geocoding, weather, and external location services

## Setup

From the `weather-ai-backend` directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/> in a browser. API documentation is available at
<http://127.0.0.1:8000/docs>.

The SQLite database is created at
`weather-ai-backend/weather_records.db`, regardless of the directory from which
Uvicorn is started.

## API summary

### Create from structured data

```http
POST /weather-queries
Content-Type: application/json

{
  "location": "Charminar, Hyderabad",
  "start_date": "2026-11-13",
  "end_date": "2026-11-17",
  "user_notes": "Outdoor sightseeing"
}
```

### Create from natural language

```http
POST /chat-query
Content-Type: application/json

{
  "query": "weather in Tokyo from 2026-11-13 to 2026-11-17"
}
```

### Read, update, and delete

```text
GET    /weather-queries
GET    /weather-queries/{id}
PUT    /weather-queries/{id}
DELETE /weather-queries/{id}
```

An update can change the location, date range, or saved notes. Changing the
location or dates refreshes the weather and travel guidance.

### Export

```text
GET /weather-queries/export?format=json
GET /weather-queries/export?format=csv
GET /weather-queries/export?format=markdown
```

## External services

- Open-Meteo Forecast API
- Open-Meteo Historical Archive API
- Open-Meteo Geocoding API
- OpenStreetMap Nominatim
- Google Maps links
- YouTube search links

The YouTube integration intentionally uses location-specific search links and
does not require a YouTube API key.

## Project layout

```text
weather-ai-backend/
  app/
    main.py
    database.py
    models.py
    schemas.py
    routers/
    services/
    static/
      index.html
      app.js
      styles.css
  requirements.txt
  weather_records.db
```

## Notes

Weather availability depends on the date range supported by Open-Meteo. The
application reports weather-provider and validation errors in the
API and in the web interface rather than returning static weather data.
