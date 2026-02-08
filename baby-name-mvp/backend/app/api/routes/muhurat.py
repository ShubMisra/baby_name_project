from fastapi import APIRouter, HTTPException
from app.services.muhurat.engine.muhurat_engine import suggest_muhurats
from app.services.muhurat.schemas.muhurat_schemas import (
    MuhuratSuggestRequest,
    MuhuratSuggestResponse,
)

router = APIRouter(prefix="/muhurat", tags=["Muhurat"])


@router.post("/suggest", response_model=MuhuratSuggestResponse)
def muhurat_suggest(payload: MuhuratSuggestRequest):
    try:
        results, meta = suggest_muhurats(
            start_date=payload.start_date,
            end_date=payload.end_date,
            location=payload.location,
            max_results=payload.max_results,
            qualities_text=payload.qualities_text,
            qualities_selected=payload.qualities_selected,
            qualities_priority=payload.qualities_priority,
            parents=payload.parents.model_dump() if payload.parents else None,
        )
        return MuhuratSuggestResponse(
            results=results,
            traits_used=meta.get("traits_used"),
            weights_used=meta.get("weights_used"),
        )
    except Exception as e:
        import traceback
        raise HTTPException(status_code=400, detail=traceback.format_exc())
