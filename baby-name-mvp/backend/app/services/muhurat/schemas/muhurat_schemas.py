from pydantic import BaseModel, Field
from typing import Optional, List
from app.services.astrology.schemas import LocationInput


class ParentDetails(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    date_of_birth: str = Field(..., description="YYYY-MM-DD")
    time_of_birth: str = Field(..., description="HH:MM")
    location: LocationInput


class ParentsInfo(BaseModel):
    mother: ParentDetails
    father: ParentDetails


class MuhuratSuggestRequest(BaseModel):
    start_date: str = Field(..., description="YYYY-MM-DD")
    end_date: str = Field(..., description="YYYY-MM-DD")
    location: LocationInput
    max_results: int = Field(default=10, ge=1, le=50)
    parents: Optional[ParentsInfo] = None
    qualities_text: Optional[str] = None
    qualities_selected: Optional[List[str]] = None
    qualities_priority: Optional[List[str]] = None


class MuhuratItem(BaseModel):
    date: str
    time: str
    nakshatra: str
    pada: int
    rashi: str
    tithi: str
    yoga: str
    karana: str
    lagna: str
    lagna_lord: Optional[str] = None
    eighth_house_rashi: str
    jupiter_rashi: str
    jupiter_strong: Optional[bool] = None
    dasha_lord: str
    ninth_lord: Optional[str] = None
    fourth_lord: Optional[str] = None
    ninth_strength: Optional[int] = None
    fourth_strength: Optional[int] = None
    parents_dasha: Optional[dict] = None
    score: int


class MuhuratSuggestResponse(BaseModel):
    status: str = "success"
    results: List[MuhuratItem]
    traits_used: Optional[List[str]] = None
    weights_used: Optional[dict] = None
