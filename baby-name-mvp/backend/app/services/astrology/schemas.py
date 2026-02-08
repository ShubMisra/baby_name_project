from pydantic import BaseModel, Field, model_validator
from typing import Optional


class LocationInput(BaseModel):
    # Lat/Lon mode
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    timezone: Optional[str] = None  # e.g. "Asia/Kolkata"

    # Place mode
    place: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    use_llm: Optional[bool] = False

    label: Optional[str] = None

    @model_validator(mode="after")
    def validate_location(self):
        has_latlon = self.latitude is not None and self.longitude is not None
        has_place = bool(self.place or self.city or self.state or self.country)
        if not has_latlon and not has_place:
            raise ValueError("location must include lat/lon or a place/city/state/country")
        return self
