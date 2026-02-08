from __future__ import annotations

import json
import os
from typing import List, Optional

from dotenv import load_dotenv

from app.services.muhurat.config.settings import (
    TRAIT_OPTIONS,
    TRAIT_PRIORITY_MULTIPLIERS,
    TRAIT_WEIGHT_OVERRIDES,
    WEIGHTS,
    SHUBHA_NAKSHATRAS,
    BENEFIC_RASHIS,
    BENEFIC_TITHIS,
    BENEFIC_YOGAS,
    BENEFIC_KARANAS,
    BENEFIC_LAGNAS,
)

# Ensure .env is loaded when running locally
load_dotenv()

def _unique_ordered(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def normalize_traits(traits: Optional[List[str]]) -> List[str]:
    if not traits:
        return []
    return [t for t in _unique_ordered(traits) if t in TRAIT_OPTIONS]


def apply_trait_weights(base_weights: dict, traits_ordered: List[str]) -> dict:
    weights = dict(base_weights)
    for idx, trait in enumerate(traits_ordered[: len(TRAIT_PRIORITY_MULTIPLIERS)]):
        multiplier = TRAIT_PRIORITY_MULTIPLIERS[idx]
        overrides = TRAIT_WEIGHT_OVERRIDES.get(trait, {})
        for k, v in overrides.items():
            weights[k] = weights.get(k, 0) + (v * multiplier)
    return weights


def llm_map_traits(text: str) -> List[str]:
    """
    Map free text to up to 3 traits from TRAIT_OPTIONS using OpenAI if configured.
    Returns an ordered list (priority order).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not text.strip():
        return []

    try:
        from openai import OpenAI
    except Exception:
        return []

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key, timeout=10.0, max_retries=0)

    prompt = (
        "You are mapping parents' free-text preferences to a fixed list of traits.\n"
        f"Allowed traits: {', '.join(TRAIT_OPTIONS)}.\n"
        "Return JSON only in this exact format:\n"
        '{"traits": ["trait1", "trait2", "trait3"]}\n'
        "Rules: choose up to 3 traits in priority order, only from the allowed list.\n"
        f"Input text: {text}\n"
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        content = resp.choices[0].message.content or ""
        data = json.loads(content)
        traits = data.get("traits", [])
        return normalize_traits(traits)
    except Exception:
        return []


def resolve_traits(
    qualities_text: Optional[str],
    qualities_selected: Optional[List[str]],
    qualities_priority: Optional[List[str]],
) -> List[str]:
    # Priority list overrides everything if provided
    priority = normalize_traits(qualities_priority)
    if priority:
        return priority

    llm_traits = llm_map_traits(qualities_text or "")
    selected = normalize_traits(qualities_selected)
    return _unique_ordered(llm_traits + selected)


def get_weights_for_traits(traits_ordered: List[str]) -> dict:
    return apply_trait_weights(WEIGHTS, traits_ordered)


# Trait-based filters for row selection (primary trait only)
TRAIT_FILTERS = {
    "health": [("lagna", BENEFIC_LAGNAS), ("tithi", BENEFIC_TITHIS)],
    "intelligence": [("yoga", BENEFIC_YOGAS), ("nakshatra", SHUBHA_NAKSHATRAS)],
    "wealth": [("rashi", BENEFIC_RASHIS), ("karana", BENEFIC_KARANAS)],
    "leadership": [("lagna", BENEFIC_LAGNAS), ("nakshatra", SHUBHA_NAKSHATRAS)],
    "spiritual": [("tithi", BENEFIC_TITHIS), ("yoga", BENEFIC_YOGAS)],
    "creativity": [("nakshatra", SHUBHA_NAKSHATRAS)],
    "stability": [("rashi", BENEFIC_RASHIS), ("lagna", BENEFIC_LAGNAS)],
    "compassion": [("tithi", BENEFIC_TITHIS), ("nakshatra", SHUBHA_NAKSHATRAS)],
    "courage": [("lagna", BENEFIC_LAGNAS), ("karana", BENEFIC_KARANAS)],
}


def passes_trait_filters(astro: dict, traits_ordered: List[str]) -> bool:
    if not traits_ordered:
        return True
    primary = traits_ordered[0]
    checks = TRAIT_FILTERS.get(primary, [])
    for field, allowed in checks:
        if astro.get(field) not in allowed:
            return False
    return True
