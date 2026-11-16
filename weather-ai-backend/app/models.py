from datetime import datetime, timezone
from sqlalchemy import Column, Date, DateTime, Float, Integer, JSON, String, Text
from app.database import Base


class WeatherRecord(Base):
    __tablename__ = "weather_records"

    id = Column(Integer, primary_key=True, index=True)
    raw_location_input = Column(String(255), nullable=False)
    resolved_location = Column(String(255), nullable=False)
    country = Column(String(100), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    current_temp_c = Column(Float, nullable=True)
    weather_summary = Column(JSON, nullable=False)      # Daily highs, lows, precipitation, wind
    travel_advisory = Column(Text, nullable=False)
    google_maps_url = Column(String(500), nullable=False)
    user_notes = Column(Text, nullable=True)

    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )