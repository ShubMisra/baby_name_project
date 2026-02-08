from __future__ import annotations

import datetime as _dt
import os
from typing import Any, Dict, Tuple, Union, Optional

import pytz
from dotenv import load_dotenv
import swisseph as swe
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from timezonefinder import TimezoneFinder

from .schemas import LocationInput
from .nakshatra_table import NAKSHATRA_PADA_SYLLABLES


# -----------------------
# CONSTANTS
# -----------------------
NAKSHATRA_LIST = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
    "Ardra", "Punarvasu", "Pushya", "Ashlesha",
    "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha",
    "Anuradha", "Jyeshtha", "Mula",
    "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati",
]

RASHI_LIST = [
    "Mesha (Aries)", "Vrishabha (Taurus)", "Mithuna (Gemini)",
    "Karka (Cancer)", "Simha (Leo)", "Kanya (Virgo)",
    "Tula (Libra)", "Vrischika (Scorpio)", "Dhanu (Sagittarius)",
    "Makara (Capricorn)", "Kumbha (Aquarius)", "Meena (Pisces)",
]

NAKSHATRA_SPAN = 13 + 1 / 3  # 13.333...
PADA_SPAN = NAKSHATRA_SPAN / 4

# Vimshottari dasha sequence and durations (years)
DASHA_SEQUENCE = [
    ("Ketu", 7),
    ("Venus", 20),
    ("Sun", 6),
    ("Moon", 10),
    ("Mars", 7),
    ("Rahu", 18),
    ("Jupiter", 16),
    ("Saturn", 19),
    ("Mercury", 17),
]

# Nakshatra lords in order for 27 nakshatras
NAKSHATRA_LORDS = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
]

# Sign lords (rulers)
SIGN_LORDS = {
    "Mesha (Aries)": "Mars",
    "Vrishabha (Taurus)": "Venus",
    "Mithuna (Gemini)": "Mercury",
    "Karka (Cancer)": "Moon",
    "Simha (Leo)": "Sun",
    "Kanya (Virgo)": "Mercury",
    "Tula (Libra)": "Venus",
    "Vrischika (Scorpio)": "Mars",
    "Dhanu (Sagittarius)": "Jupiter",
    "Makara (Capricorn)": "Saturn",
    "Kumbha (Aquarius)": "Saturn",
    "Meena (Pisces)": "Jupiter",
}

# Planet friendships (standard Vedic)
PLANET_FRIENDS = {
    "Sun": {"Moon", "Mars", "Jupiter"},
    "Moon": {"Sun", "Mercury"},
    "Mars": {"Sun", "Moon", "Jupiter"},
    "Mercury": {"Sun", "Venus"},
    "Jupiter": {"Sun", "Moon", "Mars"},
    "Venus": {"Mercury", "Saturn"},
    "Saturn": {"Mercury", "Venus"},
    "Rahu": {"Venus", "Saturn", "Mercury"},
    "Ketu": {"Mars", "Jupiter", "Sun"},
}

# Exaltation signs
EXALTED_SIGNS = {
    "Sun": "Mesha (Aries)",
    "Moon": "Vrishabha (Taurus)",
    "Mars": "Makara (Capricorn)",
    "Mercury": "Kanya (Virgo)",
    "Jupiter": "Karka (Cancer)",
    "Venus": "Meena (Pisces)",
    "Saturn": "Tula (Libra)",
    "Rahu": "Mithuna (Gemini)",
    "Ketu": "Dhanu (Sagittarius)",
}

OWN_SIGNS = {
    "Sun": {"Simha (Leo)"},
    "Moon": {"Karka (Cancer)"},
    "Mars": {"Mesha (Aries)", "Vrischika (Scorpio)"},
    "Mercury": {"Mithuna (Gemini)", "Kanya (Virgo)"},
    "Jupiter": {"Dhanu (Sagittarius)", "Meena (Pisces)"},
    "Venus": {"Vrishabha (Taurus)", "Tula (Libra)"},
    "Saturn": {"Makara (Capricorn)", "Kumbha (Aquarius)"},
}

BENEFIC_PLANETS = {"Jupiter", "Venus", "Mercury", "Moon"}


# -----------------------
# LOCATION RESOLUTION
# -----------------------
def _normalize_location(
    place_or_location: Union[str, LocationInput, dict]
) -> Tuple[float, float, str]:
    """
    Returns (lat, lon, timezone).
    Prefers offline-friendly inputs (LocationInput / dict with lat/lon/tz).
    Falls back to geocoding ONLY if a string is passed.
    """
    # LocationInput
    if isinstance(place_or_location, LocationInput):
        if place_or_location.latitude is not None and place_or_location.longitude is not None:
            tz = place_or_location.timezone or _get_timezone(
                place_or_location.latitude, place_or_location.longitude
            )
            return place_or_location.latitude, place_or_location.longitude, tz
        place = _compose_place_string(place_or_location)
        if place_or_location.use_llm:
            place = _llm_normalize_place(place) or place
        lat, lon = _geocode_place(place)
        tz = place_or_location.timezone or _get_timezone(lat, lon)
        return lat, lon, tz

    # dict
    if isinstance(place_or_location, dict):
        lat_val = place_or_location.get("latitude")
        lon_val = place_or_location.get("longitude")
        if lat_val is not None and lon_val is not None:
            lat = float(lat_val)
            lon = float(lon_val)
            tz = str(place_or_location.get("timezone") or _get_timezone(lat, lon))
            return lat, lon, tz
        place = _compose_place_string(place_or_location)
        if place_or_location.get("use_llm"):
            place = _llm_normalize_place(place) or place
        lat, lon = _geocode_place(place)
        tz = str(place_or_location.get("timezone") or _get_timezone(lat, lon))
        return lat, lon, tz

    # string => geocode (network)
    if isinstance(place_or_location, str):
        lat, lon = _geocode_place(place_or_location)
        tz = _get_timezone(lat, lon)
        return lat, lon, tz

    raise TypeError("location must be str | LocationInput | dict")


def resolve_location(place_or_location: Union[str, LocationInput, dict]) -> dict:
    """
    Resolve any supported location input to a dict with lat/lon/timezone.
    This allows callers to pre-resolve once and avoid repeated geocoding.
    """
    lat, lon, tz = _normalize_location(place_or_location)
    return {"latitude": lat, "longitude": lon, "timezone": tz}


def _compose_place_string(loc: Union[LocationInput, dict]) -> str:
    # Prefer explicit place; else compose city/state/country
    place = ""
    if isinstance(loc, LocationInput):
        place = (loc.place or "").strip()
        city = (loc.city or "").strip()
        state = (loc.state or "").strip()
        country = (loc.country or "").strip()
    else:
        place = str(loc.get("place") or "").strip()
        city = str(loc.get("city") or "").strip()
        state = str(loc.get("state") or "").strip()
        country = str(loc.get("country") or "").strip()

    if place:
        return place
    parts = [p for p in [city, state, country] if p]
    return ", ".join(parts)


def _llm_normalize_place(place: str) -> Optional[str]:
    if not place:
        return None
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except Exception:
        return None
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key, timeout=10.0, max_retries=0)
    prompt = (
        "Normalize this location into 'City, State, Country' if possible. "
        "If it's already clear, return the same. Return only the normalized string.\n"
        f"Input: {place}"
    )
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        out = (resp.choices[0].message.content or "").strip()
        return out or None
    except Exception:
        return None


def _geocode_place(place: str) -> Tuple[float, float]:
    """
    Network call. Use only when user passes a string location.
    Retries with larger timeout so it won't fail randomly.
    """
    geolocator = Nominatim(user_agent="baby-name-mvp")

    last_err: Optional[Exception] = None
    for timeout in (3, 6, 10):  # progressive timeouts
        try:
            loc = geolocator.geocode(place, timeout=timeout)
            if loc:
                return float(loc.latitude), float(loc.longitude)
        except (GeocoderTimedOut, GeocoderUnavailable) as e:
            last_err = e
            continue

    raise ValueError(f"Could not geocode place '{place}'. Error: {last_err}")


def _get_timezone(lat: float, lon: float) -> str:
    tf = TimezoneFinder()
    tz = tf.timezone_at(lat=lat, lng=lon)
    if not tz:
        raise ValueError("Could not determine timezone from lat/lon")
    return tz


# -----------------------
# CORE ASTRO
# -----------------------
def _parse_local_datetime(date_of_birth: str, time_of_birth: str, tz_name: str) -> _dt.datetime:
    """
    Accepts:
      date_of_birth: 'YYYY-MM-DD'
      time_of_birth: 'HH:MM' or 'HH:MM:SS'
    Returns tz-aware local datetime.
    """
    t = time_of_birth.strip()
    if len(t) == 5:
        t = f"{t}:00"

    naive = _dt.datetime.fromisoformat(f"{date_of_birth} {t}")
    tz = pytz.timezone(tz_name)
    return tz.localize(naive)


def calculate_moon_longitude(dt_utc: _dt.datetime) -> float:
    """
    Returns Moon longitude in degrees [0, 360).
    Swiss Ephemeris: swe.calc_ut(jd, body) returns (pos_tuple, retflag).
    pos_tuple contains 6 values: (lon, lat, dist, speed_lon, speed_lat, speed_dist)
    """
    jd = swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0,
    )

    pos, _flag = swe.calc_ut(jd, swe.MOON)
    moon_lon = float(pos[0]) % 360.0
    return moon_lon


def calculate_sun_longitude(dt_utc: _dt.datetime) -> float:
    jd = swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0,
    )
    pos, _flag = swe.calc_ut(jd, swe.SUN)
    return float(pos[0]) % 360.0


def calculate_jupiter_longitude(dt_utc: _dt.datetime) -> float:
    jd = swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0,
    )
    pos, _flag = swe.calc_ut(jd, swe.JUPITER)
    return float(pos[0]) % 360.0


def get_nakshatra_and_pada(moon_longitude: float) -> Tuple[str, int]:
    nak_index = int(moon_longitude / NAKSHATRA_SPAN)
    nakshatra = NAKSHATRA_LIST[nak_index]

    remainder = moon_longitude % NAKSHATRA_SPAN
    pada = int(remainder / PADA_SPAN) + 1
    return nakshatra, pada


def get_rashi(moon_longitude: float) -> str:
    rashi_index = int(moon_longitude / 30)
    return RASHI_LIST[rashi_index]


def get_sign_lord(rashi: str) -> str:
    return SIGN_LORDS[rashi]


def _normalize_cusps(cusps: list) -> list:
    # Swiss Ephemeris returns 13 values (index 1..12 used).
    # Ensure we have a 13-length list with dummy at index 0.
    if len(cusps) == 13:
        return list(cusps)
    if len(cusps) == 12:
        return [0.0] + list(cusps)
    raise ValueError(f"Unexpected cusps length: {len(cusps)}")


def house_for_longitude(cusps: list, lon: float) -> int:
    """
    Determine house number for a longitude based on cusp list.
    cusps is 1-indexed list from swe.houses.
    """
    cusps = _normalize_cusps(cusps)
    lon = lon % 360.0
    for i in range(1, 13):
        start = cusps[i] % 360.0
        end = cusps[1] % 360.0 if i == 12 else cusps[i + 1] % 360.0
        if start <= end:
            if start <= lon < end:
                return i
        else:
            # wrap
            if lon >= start or lon < end:
                return i
    return 1


def compute_chart(dt_utc: _dt.datetime, lat: float, lon: float) -> dict:
    jd = swe.julday(
        dt_utc.year,
        dt_utc.month,
        dt_utc.day,
        dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0,
    )
    cusps, ascmc = swe.houses(jd, lat, lon, b"P")
    cusps = _normalize_cusps(cusps)
    asc_lon = float(ascmc[0]) % 360.0
    lagna_rashi = get_rashi(asc_lon)
    lagna_lord = get_sign_lord(lagna_rashi)

    planets = {
        "Sun": swe.SUN,
        "Moon": swe.MOON,
        "Mars": swe.MARS,
        "Mercury": swe.MERCURY,
        "Jupiter": swe.JUPITER,
        "Venus": swe.VENUS,
        "Saturn": swe.SATURN,
        "Rahu": swe.MEAN_NODE,
    }
    planet_lons = {}
    planet_rashis = {}
    planet_houses = {}
    for name, body in planets.items():
        pos, _flag = swe.calc_ut(jd, body)
        plon = float(pos[0]) % 360.0
        planet_lons[name] = plon
        planet_rashis[name] = get_rashi(plon)
        planet_houses[name] = house_for_longitude(cusps, plon)
    # Ketu is opposite Rahu
    ketu_lon = (planet_lons["Rahu"] + 180.0) % 360.0
    planet_lons["Ketu"] = ketu_lon
    planet_rashis["Ketu"] = get_rashi(ketu_lon)
    planet_houses["Ketu"] = house_for_longitude(cusps, ketu_lon)

    return {
        "jd": jd,
        "cusps": cusps,
        "asc_lon": asc_lon,
        "lagna_rashi": lagna_rashi,
        "lagna_lord": lagna_lord,
        "planet_lons": planet_lons,
        "planet_rashis": planet_rashis,
        "planet_houses": planet_houses,
    }


def is_planet_strong(planet: str, rashi: str, house: int) -> bool:
    if planet in EXALTED_SIGNS and rashi == EXALTED_SIGNS[planet]:
        return True
    if planet in OWN_SIGNS and rashi in OWN_SIGNS[planet]:
        return True
    if house in (1, 4, 7, 10):  # kendra
        return True
    return False


def get_recommended_syllables(nakshatra: str, pada: int):
    table = NAKSHATRA_PADA_SYLLABLES.get(nakshatra) or {}
    return table.get(pada, [])


TITHI_LIST = [
    "Pratipada", "Dvitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima",
    "Pratipada", "Dvitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya",
]

YOGA_LIST = [
    "Vishkumbha", "Preeti", "Ayushman", "Saubhagya", "Shobhana",
    "Atiganda", "Sukarma", "Dhriti", "Shoola", "Ganda",
    "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra",
    "Siddhi", "Vyatipata", "Variyana", "Parigha", "Shiva",
    "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma",
    "Indra", "Vaidhriti",
]

KARANA_LIST = [
    "Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti",
] * 8 + ["Shakuni", "Chatushpada", "Naga", "Kimstughna"]


def get_tithi(moon_longitude: float, sun_longitude: float) -> str:
    diff = (moon_longitude - sun_longitude) % 360.0
    index = int(diff / 12.0)
    return TITHI_LIST[index]


def get_yoga(moon_longitude: float, sun_longitude: float) -> str:
    s = (moon_longitude + sun_longitude) % 360.0
    index = int(s / (360.0 / 27.0))
    return YOGA_LIST[index]


def get_karana(moon_longitude: float, sun_longitude: float) -> str:
    diff = (moon_longitude - sun_longitude) % 360.0
    index = int(diff / 6.0)
    return KARANA_LIST[index]


def get_lagna(jd_ut: float, lat: float, lon: float) -> str:
    # Houses returns ascendant as the first value
    asc, *_rest = swe.houses(jd_ut, lat, lon, b"P")
    asc = _normalize_cusps(asc)
    lagna_lon = float(asc[0]) % 360.0
    return get_rashi(lagna_lon)


def get_eighth_house_rashi(jd_ut: float, lat: float, lon: float) -> str:
    cusps, _ascmc = swe.houses(jd_ut, lat, lon, b"P")
    cusps = _normalize_cusps(cusps)
    eighth_cusp = float(cusps[7]) % 360.0  # 8th house cusp
    return get_rashi(eighth_cusp)


def get_nakshatra_index(moon_longitude: float) -> int:
    return int(moon_longitude / NAKSHATRA_SPAN)


def get_dasha_lord(birth_dt_utc: _dt.datetime, target_dt_utc: _dt.datetime) -> str:
    """
    Vimshottari Mahadasha lord at target datetime.
    Uses moon nakshatra at birth.
    """
    moon_lon = calculate_moon_longitude(birth_dt_utc)
    nak_idx = get_nakshatra_index(moon_lon)
    lord = NAKSHATRA_LORDS[nak_idx]

    # Fraction remaining in nakshatra at birth
    remainder = moon_lon % NAKSHATRA_SPAN
    fraction_left = (NAKSHATRA_SPAN - remainder) / NAKSHATRA_SPAN

    # Find starting index in sequence
    seq = [x[0] for x in DASHA_SEQUENCE]
    start_idx = seq.index(lord)

    # Remaining years in current dasha at birth
    start_years = DASHA_SEQUENCE[start_idx][1] * fraction_left

    # Total years elapsed since birth to target
    years_elapsed = (target_dt_utc - birth_dt_utc).total_seconds() / (365.25 * 24 * 3600)
    if years_elapsed < 0:
        years_elapsed = 0

    if years_elapsed < start_years:
        return lord

    years_elapsed -= start_years
    idx = (start_idx + 1) % len(DASHA_SEQUENCE)
    while True:
        dasha_years = DASHA_SEQUENCE[idx][1]
        if years_elapsed < dasha_years:
            return DASHA_SEQUENCE[idx][0]
        years_elapsed -= dasha_years
        idx = (idx + 1) % len(DASHA_SEQUENCE)

# -----------------------
# PUBLIC API
# -----------------------
def calculate_astrology(
    date_of_birth: str,
    time_of_birth: str,
    place_of_birth: Union[str, LocationInput, dict],
) -> Dict[str, Any]:
    lat, lon, tz_name = _normalize_location(place_of_birth)

    local_dt = _parse_local_datetime(date_of_birth, time_of_birth, tz_name)
    dt_utc = local_dt.astimezone(pytz.UTC)

    moon_lon = calculate_moon_longitude(dt_utc)
    sun_lon = calculate_sun_longitude(dt_utc)
    jupiter_lon = calculate_jupiter_longitude(dt_utc)

    chart = compute_chart(dt_utc, lat, lon)
    jd = chart["jd"]

    nakshatra, pada = get_nakshatra_and_pada(moon_lon)
    rashi = get_rashi(moon_lon)
    tithi = get_tithi(moon_lon, sun_lon)
    yoga = get_yoga(moon_lon, sun_lon)
    karana = get_karana(moon_lon, sun_lon)
    lagna = get_lagna(jd, lat, lon)
    eighth_house_rashi = get_eighth_house_rashi(jd, lat, lon)
    jupiter_rashi = get_rashi(jupiter_lon)
    dasha_lord = get_dasha_lord(dt_utc, dt_utc)
    lagna_lord = chart["lagna_lord"]
    ninth_house_rashi = get_rashi(chart["cusps"][9])
    fourth_house_rashi = get_rashi(chart["cusps"][4])
    ninth_lord = get_sign_lord(ninth_house_rashi)
    fourth_lord = get_sign_lord(fourth_house_rashi)

    ninth_strength = sum(
        1 for p, h in chart["planet_houses"].items()
        if h == 9 and p in BENEFIC_PLANETS
    )
    fourth_strength = sum(
        1 for p, h in chart["planet_houses"].items()
        if h == 4 and p in BENEFIC_PLANETS
    )

    jup_house = chart["planet_houses"].get("Jupiter")
    jup_strong = is_planet_strong("Jupiter", chart["planet_rashis"]["Jupiter"], jup_house)
    syllables = get_recommended_syllables(nakshatra, pada)

    return {
        "moon_longitude": round(moon_lon, 6),
        "sun_longitude": round(sun_lon, 6),
        "jupiter_longitude": round(jupiter_lon, 6),
        "timezone": tz_name,
        "utc_datetime": dt_utc.isoformat(),
        "latitude": lat,
        "longitude": lon,
        "nakshatra": nakshatra,
        "pada": pada,
        "rashi": rashi,
        "tithi": tithi,
        "yoga": yoga,
        "karana": karana,
        "lagna": lagna,
        "lagna_lord": lagna_lord,
        "eighth_house_rashi": eighth_house_rashi,
        "jupiter_rashi": jupiter_rashi,
        "jupiter_strong": jup_strong,
        "dasha_lord": dasha_lord,
        "ninth_lord": ninth_lord,
        "fourth_lord": fourth_lord,
        "ninth_strength": ninth_strength,
        "fourth_strength": fourth_strength,
        "recommended_syllables": syllables,
    }


def calculate_dasha_lord_for_birth(
    date_of_birth: str,
    time_of_birth: str,
    place_of_birth: Union[str, LocationInput, dict],
    target_dt_utc: _dt.datetime,
) -> str:
    lat, lon, tz_name = _normalize_location(place_of_birth)
    local_dt = _parse_local_datetime(date_of_birth, time_of_birth, tz_name)
    birth_dt_utc = local_dt.astimezone(pytz.UTC)
    return get_dasha_lord(birth_dt_utc, target_dt_utc)


def calculate_parent_meta(
    date_of_birth: str,
    time_of_birth: str,
    place_of_birth: Union[str, LocationInput, dict],
) -> dict:
    lat, lon, tz_name = _normalize_location(place_of_birth)
    local_dt = _parse_local_datetime(date_of_birth, time_of_birth, tz_name)
    birth_dt_utc = local_dt.astimezone(pytz.UTC)
    chart = compute_chart(birth_dt_utc, lat, lon)

    fifth_rashi = get_rashi(chart["cusps"][5])
    ninth_rashi = get_rashi(chart["cusps"][9])
    fifth_lord = get_sign_lord(fifth_rashi)
    ninth_lord = get_sign_lord(ninth_rashi)

    jup_house = chart["planet_houses"].get("Jupiter")
    jup_strong = is_planet_strong("Jupiter", chart["planet_rashis"]["Jupiter"], jup_house)

    return {
        "fifth_lord": fifth_lord,
        "ninth_lord": ninth_lord,
        "jupiter_strong": jup_strong,
    }
