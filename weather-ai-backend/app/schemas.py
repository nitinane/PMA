from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, model_validator


class WeatherQueryCreate(BaseModel):
    location: str = Field(
        ...,
        min_length=2,
        max_length=120,
        examples=["Charminar, Hyderabad", "500001", "17.3616, 78.4747"],
    )
    start_date: date
    end_date: date
    user_notes: Optional[str] = Field(None, max_length=300)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be earlier than start_date.")
        if (self.end_date - self.start_date).days > 14:
            raise ValueError("Date range cannot exceed 14 days per request.")
        if self.start_date.year < 1940:
            raise ValueError("Historical data is only supported from 1940 onwards.")
        return self


class WeatherQueryUpdate(BaseModel):
    location: Optional[str] = Field(None, min_length=2, max_length=120)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    user_notes: Optional[str] = Field(None, max_length=300)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date cannot be earlier than start_date.")
        if (
            self.start_date
            and self.end_date
            and (self.end_date - self.start_date).days > 14
        ):
            raise ValueError("Date range cannot exceed 14 days per request.")
        if self.start_date and self.start_date.year < 1940:
            raise ValueError("Historical data is only supported from 1940 onwards.")
        return self

class WeatherRecordResponse(BaseModel):
    id: int
    raw_location_input: str
    resolved_location: str
    country: Optional[str]
    latitude: float
    longitude: float
    start_date: date
    end_date: date
    current_temp_c: Optional[float]
    weather_summary: dict[str, Any]
    travel_advisory: str
    google_maps_url: str
    user_notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}