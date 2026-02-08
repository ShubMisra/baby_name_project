from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

from app.services.astrology.astrology_engine import (
    calculate_astrology,
    calculate_dasha_lord_for_birth,
    resolve_location,
    calculate_parent_meta,
)
from app.services.astrology.schemas import LocationInput

from app.services.muhurat.config.settings import (
    TIME_SLOT_MINUTES,
    DAY_START_HOUR,
    DAY_END_HOUR,
    HARD_CAP_MULTIPLIER,
)
from app.services.muhurat.utils.kalam import is_rahu_kalam
from app.services.muhurat.utils.scoring import compute_score
from app.services.muhurat.utils.qualities import (
    resolve_traits,
    get_weights_for_traits,
    passes_trait_filters,
)


def _date_range(start: datetime.date, end: datetime.date):
    cur = start
    while cur <= end:
        yield cur
        cur += datetime.timedelta(days=1)


def suggest_muhurats(
    start_date: str,
    end_date: str,
    location: LocationInput,
    max_results: int = 10,
    qualities_text: Optional[str] = None,
    qualities_selected: Optional[List[str]] = None,
    qualities_priority: Optional[List[str]] = None,
    parents: Optional[dict] = None,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Muhurat Suggestion Engine (MVP)

    - Uses offline-friendly LocationInput (lat/lon/timezone) → no geocoding
    - Calculates nakshatra/pada/rashi per candidate time slot via calculate_astrology()
    - Skips Rahu Kalam
    - Scores using scoring utils
    - Bounded runtime using:
        * config-based window (DAY_START_HOUR → DAY_END_HOUR)
        * config TIME_SLOT_MINUTES
        * hard cap to prevent runaway loops
    """

    sd = datetime.date.fromisoformat(start_date)
    ed = datetime.date.fromisoformat(end_date)
    if ed < sd:
        raise ValueError("end_date must be >= start_date")
    if (ed - sd).days > 365:
        raise ValueError("date range must be <= 365 days")

    traits = resolve_traits(qualities_text, qualities_selected, qualities_priority)
    weights = get_weights_for_traits(traits)

    # Resolve candidate location once (avoids per-slot geocoding/LLM)
    resolved_location = resolve_location(location)

    # Resolve parents locations once (if provided)
    parents_resolved = None
    parents_meta = None
    if parents and parents.get("mother") and parents.get("father"):
        mother = dict(parents["mother"])
        father = dict(parents["father"])
        mother["location"] = resolve_location(mother["location"])
        father["location"] = resolve_location(father["location"])
        parents_resolved = {"mother": mother, "father": father}
        parents_meta = {
            "mother": calculate_parent_meta(
                mother["date_of_birth"],
                mother["time_of_birth"],
                mother["location"],
            ),
            "father": calculate_parent_meta(
                father["date_of_birth"],
                father["time_of_birth"],
                father["location"],
            ),
        }

    # Hard cap prevents huge scans if user gives large ranges
    hard_cap = max(50, int(max_results) * int(HARD_CAP_MULTIPLIER))

    def _run_scan(strict_filters: bool, min_score: int) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        seen_keys = set()

        for d in _date_range(sd, ed):
            # scan only within configured hours
            for hour in range(int(DAY_START_HOUR), int(DAY_END_HOUR) + 1):
                for minute in range(0, 60, int(TIME_SLOT_MINUTES)):
                    # Avoid generating slot past end hour boundary
                    if hour == int(DAY_END_HOUR) and minute > 0:
                        break

                    time_str = f"{hour:02d}:{minute:02d}"
                    local_dt = datetime.datetime.fromisoformat(f"{d.isoformat()} {time_str}")

                    if is_rahu_kalam(local_dt):
                        continue

                    # ✅ FIX: correct arg name is place_of_birth (and it accepts LocationInput)
                    astro = calculate_astrology(
                        date_of_birth=d.isoformat(),
                        time_of_birth=time_str,
                        place_of_birth=resolved_location,
                    )

                    # Parent dasha at candidate time (if provided)
                    parents_dasha = None
                    if parents_resolved:
                        mother = parents_resolved["mother"]
                        father = parents_resolved["father"]
                        candidate_utc = datetime.datetime.fromisoformat(astro["utc_datetime"])
                        parents_dasha = {
                            "mother": calculate_dasha_lord_for_birth(
                                mother["date_of_birth"],
                                mother["time_of_birth"],
                                mother["location"],
                                candidate_utc,
                            ),
                            "father": calculate_dasha_lord_for_birth(
                                father["date_of_birth"],
                                father["time_of_birth"],
                                father["location"],
                                candidate_utc,
                            ),
                        }

                    if strict_filters and traits and not passes_trait_filters(astro, traits):
                        continue

                    astro["parents_dasha"] = parents_dasha
                    score = int(compute_score(astro, parents_meta, weights))
                    if score < min_score:
                        continue

                    # De-duplicate by date + key astro factors
                    key = (
                        d.isoformat(),
                        astro["nakshatra"],
                        astro["pada"],
                        astro["rashi"],
                        astro["tithi"],
                        astro["yoga"],
                        astro["karana"],
                        astro["lagna"],
                        astro["eighth_house_rashi"],
                        astro["jupiter_rashi"],
                        astro["dasha_lord"],
                    )
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)

                    results.append(
                        {
                            "date": d.isoformat(),
                            "time": time_str,
                            "nakshatra": astro["nakshatra"],
                            "pada": astro["pada"],
                            "rashi": astro["rashi"],
                            "tithi": astro["tithi"],
                            "yoga": astro["yoga"],
                            "karana": astro["karana"],
                            "lagna": astro["lagna"],
                            "lagna_lord": astro.get("lagna_lord"),
                            "eighth_house_rashi": astro["eighth_house_rashi"],
                            "jupiter_rashi": astro["jupiter_rashi"],
                            "jupiter_strong": astro.get("jupiter_strong"),
                            "dasha_lord": astro["dasha_lord"],
                            "ninth_lord": astro.get("ninth_lord"),
                            "fourth_lord": astro.get("fourth_lord"),
                            "ninth_strength": astro.get("ninth_strength"),
                            "fourth_strength": astro.get("fourth_strength"),
                            "parents_dasha": astro.get("parents_dasha"),
                            "score": score,
                        }
                    )

                    # Keep runtime bounded
                    if len(results) >= hard_cap:
                        break
                if len(results) >= hard_cap:
                    break
            if len(results) >= hard_cap:
                break

        return results

    results = _run_scan(strict_filters=True, min_score=10)
    if not results:
        # Fallback: relax filters and score threshold
        results = _run_scan(strict_filters=False, min_score=0)

    # Higher score first; tie-breaker earliest date/time
    results.sort(key=lambda x: (-x["score"], x["date"], x["time"]))
    return results[:max_results], {"traits_used": traits, "weights_used": weights}
