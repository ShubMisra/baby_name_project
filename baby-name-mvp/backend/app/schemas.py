from datetime import date, time
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class PersonDetails(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    date_of_birth: date
    time_of_birth: Optional[time] = None
    place_of_birth: str = Field(..., min_length=2, max_length=200)


class ParentBlock(BaseModel):
    father_details: PersonDetails
    mother_details: PersonDetails


DailyWindow = Literal["morning", "afternoon", "evening", "night", "any"]
DeliveryType = Literal["either", "c_section_planned", "normal"]
PriorityGoal = Literal["health", "intelligence", "wealth", "leadership", "spiritual", "overall_balance"]


class MuhuratRequest(BaseModel):
    delivery_window_start_date: date
    delivery_window_end_date: date
    delivery_city: str = Field(..., min_length=2, max_length=200)

    delivery_type: DeliveryType = "either"
    daily_time_window: DailyWindow = "any"

    daily_start_time: Optional[time] = None
    daily_end_time: Optional[time] = None

    avoid_weekdays: List[str] = Field(default_factory=list)
    avoid_dates: List[date] = Field(default_factory=list)

    prefer_nakshatras: List[str] = Field(default_factory=list)
    avoid_nakshatras: List[str] = Field(default_factory=list)

    priority_goal: List[PriorityGoal] = Field(default_factory=list, max_length=2)

    number_of_suggestions: Literal[1, 3, 5, 10] = 5
    slot_granularity_minutes: Literal[15, 30, 60] = 30
    include_kundli_summary: bool = True

    acknowledge_medical_priority: bool = Field(...)

    @field_validator("acknowledge_medical_priority")
    @classmethod
    def must_ack(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("acknowledge_medical_priority must be true")
        return v

    @field_validator("delivery_window_end_date")
    @classmethod
    def end_after_start(cls, end_date: date, info):
        start_date = info.data.get("delivery_window_start_date")
        if start_date and end_date < start_date:
            raise ValueError("delivery_window_end_date must be >= delivery_window_start_date")
        return end_date


class MuhuratSuggestRequest(ParentBlock):
    muhurat_request: MuhuratRequest


Gender = Literal["male", "female", "neutral"]
NameLength = Literal["short", "medium", "long", "any"]
Origin = Literal["sanskrit", "hindi", "modern_indian", "traditional", "contemporary"]
NumerologySystem = Literal["chaldean", "pythagorean", "vedic"]


class BabyDetails(BaseModel):
    gender: Gender
    date_of_birth: date
    time_of_birth: time
    place_of_birth: str = Field(..., min_length=2, max_length=200)


class Preferences(BaseModel):
    starting_letters: List[str] = Field(default_factory=list, max_length=5)
    origins: List[Origin] = Field(..., min_length=1)
    name_length: NameLength = "any"
    meaning_themes: List[str] = Field(default_factory=list)

    traditional_modern_scale: int = Field(..., ge=0, le=10)
    number_of_suggestions: Literal[5, 10, 15, 20] = 10

    avoid_names: List[str] = Field(default_factory=list)


class AdvancedOptions(BaseModel):
    numerology_system: NumerologySystem = "chaldean"
    preferred_lucky_number: Optional[int] = Field(default=None, ge=1, le=9)

    include_meanings: bool = True
    include_numerology_report: bool = True
    include_famous_personalities: bool = False


class NameSuggestRequest(ParentBlock):
    baby_details: BabyDetails
    preferences: Preferences
    advanced_options: Optional[AdvancedOptions] = None