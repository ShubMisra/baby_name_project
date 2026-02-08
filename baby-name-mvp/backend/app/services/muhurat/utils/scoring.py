from app.services.muhurat.config.settings import (
    SHUBHA_NAKSHATRAS,
    BENEFIC_RASHIS,
    BENEFIC_TITHIS,
    BENEFIC_YOGAS,
    BENEFIC_KARANAS,
    BENEFIC_LAGNAS,
    BENEFIC_JUPITER_RASHIS,
    BENEFIC_DASHA_LORDS,
    WEIGHTS,
)

from app.services.astrology.astrology_engine import (
    PLANET_FRIENDS,
    NAKSHATRA_LORDS,
    NAKSHATRA_LIST,
)


def score_nakshatra(nakshatra: str, weights: dict = WEIGHTS) -> int:
    return weights["nakshatra"] if nakshatra in SHUBHA_NAKSHATRAS else 0


def score_rashi(rashi: str, weights: dict = WEIGHTS) -> int:
    return weights["rashi"] if rashi in BENEFIC_RASHIS else 0


def score_pada(pada: int, weights: dict = WEIGHTS) -> int:
    # Simple heuristic: favor 1st and 4th pada slightly
    return weights["pada"] if pada in (1, 4) else 0


def score_tithi(tithi: str, weights: dict = WEIGHTS) -> int:
    return weights["tithi"] if tithi in BENEFIC_TITHIS else 0


def score_yoga(yoga: str, weights: dict = WEIGHTS) -> int:
    return weights["yoga"] if yoga in BENEFIC_YOGAS else 0


def score_karana(karana: str, weights: dict = WEIGHTS) -> int:
    return weights["karana"] if karana in BENEFIC_KARANAS else 0


def score_lagna(lagna: str, weights: dict = WEIGHTS) -> int:
    return weights["lagna"] if lagna in BENEFIC_LAGNAS else 0


def score_eighth_house(eighth_house_rashi: str, weights: dict = WEIGHTS) -> int:
    return weights["eighth_house"] if eighth_house_rashi in BENEFIC_LAGNAS else 0


def score_jupiter(jupiter_rashi: str, weights: dict = WEIGHTS) -> int:
    return weights["jupiter"] if jupiter_rashi in BENEFIC_JUPITER_RASHIS else 0


def score_dasha(dasha_lord: str, weights: dict = WEIGHTS) -> int:
    return weights["dasha"] if dasha_lord in BENEFIC_DASHA_LORDS else 0


def score_parents_dasha(parents_dasha: dict, weights: dict = WEIGHTS) -> int:
    if not parents_dasha:
        return 0
    mother = parents_dasha.get("mother")
    father = parents_dasha.get("father")
    if mother in BENEFIC_DASHA_LORDS and father in BENEFIC_DASHA_LORDS:
        return weights["parents_dasha"]
    return 0


def score_lagna_friendship(baby_lagna_lord: str, parents_dasha: dict, weights: dict = WEIGHTS) -> int:
    if not parents_dasha:
        return 0
    mother = parents_dasha.get("mother")
    father = parents_dasha.get("father")
    if not mother or not father:
        return 0
    friends = PLANET_FRIENDS.get(baby_lagna_lord, set())
    if mother in friends and father in friends:
        return weights["lagna_friendship"]
    return 0


def score_arrival_indicator(parent_5th_lord: str, parent_9th_lord: str, parent_dasha: str, weights: dict) -> int:
    if not parent_dasha:
        return 0
    if parent_dasha in {parent_5th_lord, parent_9th_lord}:
        return weights["arrival_indicator"]
    return 0


def score_dasha_sandhi(parent_dasha: str, weights: dict) -> int:
    # Placeholder: if unknown transitions, no penalty
    if not parent_dasha:
        return 0
    return 0


def score_jupiter_compensation(parent_jupiter_strong: bool, baby_jupiter_strong: bool, weights: dict) -> int:
    if parent_jupiter_strong is False and baby_jupiter_strong is True:
        return weights["jupiter_compensation"]
    return 0


def score_dasha_clash(parent_dasha: str, baby_start_dasha: str, weights: dict) -> int:
    if not parent_dasha or not baby_start_dasha:
        return 0
    if (parent_dasha == "Rahu" and baby_start_dasha == "Ketu") or (
        parent_dasha == "Ketu" and baby_start_dasha == "Rahu"
    ):
        return -weights["dasha_clash"]
    return 0


def score_house_strength(ninth_strength: int, fourth_strength: int, weights: dict) -> int:
    return (ninth_strength * weights["ninth_house_strength"]) + (
        fourth_strength * weights["fourth_house_strength"]
    )


def baby_start_dasha_lord(nakshatra: str) -> str:
    idx = NAKSHATRA_LIST.index(nakshatra)
    return NAKSHATRA_LORDS[idx]


def _max_possible(weights: dict = WEIGHTS) -> int:
    return (
        int(weights["nakshatra"])
        + int(weights["rashi"])
        + int(weights["pada"])
        + int(weights["tithi"])
        + int(weights["yoga"])
        + int(weights["karana"])
        + int(weights["lagna"])
        + int(weights["eighth_house"])
        + int(weights["jupiter"])
        + int(weights["dasha"])
        + int(weights["parents_dasha"])
        + int(weights["lagna_friendship"])
        + int(weights["arrival_indicator"]) * 2
        + int(weights["jupiter_compensation"]) * 2
        + int(weights["dasha_clash"]) * 2
        + int(weights["ninth_house_strength"])
        + int(weights["fourth_house_strength"])
        + int(weights["baby_start_dasha"])
    )


def compute_score(astro: dict, parents_meta: dict | None, weights: dict = WEIGHTS) -> int:
    raw = (
        int(score_nakshatra(astro["nakshatra"], weights))
        + int(score_rashi(astro["rashi"], weights))
        + int(score_pada(astro["pada"], weights))
        + int(score_tithi(astro["tithi"], weights))
        + int(score_yoga(astro["yoga"], weights))
        + int(score_karana(astro["karana"], weights))
        + int(score_lagna(astro["lagna"], weights))
        + int(score_eighth_house(astro["eighth_house_rashi"], weights))
        + int(score_jupiter(astro["jupiter_rashi"], weights))
        + int(score_dasha(astro["dasha_lord"], weights))
        + int(score_parents_dasha(astro.get("parents_dasha"), weights))
    )

    # Baby start dasha
    baby_start = baby_start_dasha_lord(astro["nakshatra"])

    # Parent interplay
    if parents_meta:
        mother = parents_meta.get("mother", {})
        father = parents_meta.get("father", {})
        parents_dasha = astro.get("parents_dasha") or {}

        raw += int(score_lagna_friendship(astro["lagna_lord"], parents_dasha, weights))

        raw += int(
            score_arrival_indicator(
                mother.get("fifth_lord"),
                mother.get("ninth_lord"),
                parents_dasha.get("mother"),
                weights,
            )
        )
        raw += int(
            score_arrival_indicator(
                father.get("fifth_lord"),
                father.get("ninth_lord"),
                parents_dasha.get("father"),
                weights,
            )
        )

        raw += int(
            score_dasha_clash(parents_dasha.get("mother"), baby_start, weights)
        )
        raw += int(
            score_dasha_clash(parents_dasha.get("father"), baby_start, weights)
        )

        raw += int(
            score_jupiter_compensation(
                mother.get("jupiter_strong"),
                astro.get("jupiter_strong"),
                weights,
            )
        )
        raw += int(
            score_jupiter_compensation(
                father.get("jupiter_strong"),
                astro.get("jupiter_strong"),
                weights,
            )
        )

    raw += int(score_house_strength(astro.get("ninth_strength", 0), astro.get("fourth_strength", 0), weights))

    raw += int(weights["baby_start_dasha"]) if baby_start else 0
    max_score = _max_possible(weights)
    if max_score <= 0:
        return 0
    return int(round((raw / max_score) * 100))
