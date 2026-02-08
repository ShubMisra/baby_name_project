from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple
import time

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable, GeocoderTimedOut
from timezonefinder import TimezoneFinder


@dataclass
class GeoConfig:
    user_agent: str
    timeout_sec: float
    retries: int
    retry_sleep_sec: float


def get_timezone(lat: float, lon: float) -> str:
    tf = TimezoneFinder()
    tz = tf.timezone_at(lat=lat, lng=lon)
    if not tz:
        raise ValueError("Could not determine timezone from lat/lon")
    return tz


def geocode_place(place: str, cfg: GeoConfig) -> Tuple[float, float]:
    """
    Online geocoding (Nominatim). Retries are configurable.
    """
    geolocator = Nominatim(user_agent=cfg.user_agent, timeout=cfg.timeout_sec)

    last_exc: Optional[Exception] = None
    for _ in range(max(cfg.retries, 1)):
        try:
            loc = geolocator.geocode(place, addressdetails=False)
            if not loc:
                raise ValueError(f"Could not geocode place: {place}")
            return float(loc.latitude), float(loc.longitude)
        except (GeocoderUnavailable, GeocoderTimedOut) as e:
            last_exc = e
            time.sleep(cfg.retry_sleep_sec)

    raise GeocoderUnavailable(f"Geocoding failed after retries: {place}. Last error: {last_exc}")