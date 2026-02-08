import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ApiRequestLog
from app.schemas import MuhuratSuggestRequest, NameSuggestRequest
from app.services.muhurat.engine.muhurat_engine import suggest_muhurats

router = APIRouter(prefix="/api/v1")


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/muhurat/suggest")
def muhurat_suggest(payload: MuhuratSuggestRequest, db: Session = Depends(get_db)):
    req = payload.muhurat_request
    tz = "Asia/Kolkata"  # MVP fixed (later infer from city)

    top = suggest_muhurats(
        start_date=req.delivery_window_start_date,
        end_date=req.delivery_window_end_date,
        granularity_minutes=req.slot_granularity_minutes,
        daily_time_window=req.daily_time_window,
        daily_start_time=req.daily_start_time,
        daily_end_time=req.daily_end_time,
        avoid_weekdays=req.avoid_weekdays,
        avoid_dates=req.avoid_dates,
        priority_goal=req.priority_goal,
        top_n=req.number_of_suggestions,
    )

    suggestions = []
    for i, item in enumerate(top, start=1):
        dt = item.dt_local
        suggestions.append({
            "rank": i,
            "datetime_local": dt.isoformat(),
            "timezone": tz,
            "panchang": {  # placeholder until Swiss Ephemeris is added
                "weekday": dt.strftime("%A"),
                "tithi": "TBD",
                "nakshatra": "TBD",
                "yoga": "TBD"
            },
            "score": item.score,
            "reason": item.reasons
        })

    response = {
        "status": "success",
        "inputs_summary": {
            "delivery_window_start_date": str(req.delivery_window_start_date),
            "delivery_window_end_date": str(req.delivery_window_end_date),
            "delivery_city": req.delivery_city,
            "timezone": tz,
            "slot_granularity_minutes": req.slot_granularity_minutes
        },
        "suggestions": suggestions
    }

    db.add(ApiRequestLog(
        endpoint="/api/v1/muhurat/suggest",
        request_payload=json.dumps(payload.model_dump(mode="json")),
        response_payload=json.dumps(response),
    ))
    db.commit()

    return response


@router.post("/names/suggest")
def names_suggest(payload: NameSuggestRequest, db: Session = Depends(get_db)):
    prefs = payload.preferences
    count = prefs.number_of_suggestions

    dummy = [
        {"name": "Aarav", "meaning": "Peaceful", "origin": "sanskrit", "traditional_score": 7},
        {"name": "Vivaan", "meaning": "Full of life", "origin": "sanskrit", "traditional_score": 6},
        {"name": "Aditya", "meaning": "Sun", "origin": "sanskrit", "traditional_score": 8},
        {"name": "Kabir", "meaning": "Great", "origin": "hindi", "traditional_score": 7},
        {"name": "Kiara", "meaning": "Bright", "origin": "modern_indian", "traditional_score": 5},
    ]

    avoid = {x.strip().lower() for x in prefs.avoid_names}
    filtered = [n for n in dummy if n["origin"] in prefs.origins and n["name"].lower() not in avoid]

    if prefs.starting_letters:
        starts = tuple(s.lower() for s in prefs.starting_letters)
        filtered = [n for n in filtered if n["name"].lower().startswith(starts)]

    filtered = (filtered * 10)[:count]

    suggestions = []
    for i, n in enumerate(filtered[:count], start=1):
        suggestions.append({
            "rank": i,
            "name": n["name"],
            "gender": payload.baby_details.gender,
            "meaning": n["meaning"],
            "origin": n["origin"],
            "numerology_number": 6,
            "compatibility_score": 95 - i,
            "nakshatra_match": True,
            "syllable_match": (prefs.starting_letters[0] if prefs.starting_letters else n["name"][0]),
            "length": len(n["name"]),
            "traditional_score": n["traditional_score"],
        })

    response = {
        "status": "success",
        "calculation_details": {
            "baby_nakshatra": "TBD",
            "baby_pada": "TBD",
            "baby_rashi": "TBD"
        },
        "name_suggestions": suggestions
    }

    db.add(ApiRequestLog(
        endpoint="/api/v1/names/suggest",
        request_payload=json.dumps(payload.model_dump(mode="json")),
        response_payload=json.dumps(response),
    ))
    db.commit()

    return response