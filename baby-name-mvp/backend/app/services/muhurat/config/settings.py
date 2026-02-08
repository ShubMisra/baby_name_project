"""
Central configuration for Muhurat engine
ALL values configurable & override-friendly
"""

# Slot resolution (minutes)
TIME_SLOT_MINUTES = 30

# Daily scan window (24h clock, local time)
# These bound the time slots that the engine will consider.
DAY_START_HOUR = 6
DAY_END_HOUR = 20

# Safety cap multiplier for max_results (prevents runaway loops)
HARD_CAP_MULTIPLIER = 5

# Nakshatra categories
SHUBHA_NAKSHATRAS = {
    "Rohini",
    "Mrigashira",
    "Punarvasu",
    "Pushya",
    "Hasta",
    "Anuradha",
    "Uttara Phalguni",
    "Uttara Ashadha",
    "Uttara Bhadrapada",
    "Revati"
}

# Benefic Rashis
BENEFIC_RASHIS = {
    "Vrishabha (Taurus)",
    "Karka (Cancer)",
    "Tula (Libra)",
    "Meena (Pisces)"
}

# Benefic Tithis (traditional auspicious set)
BENEFIC_TITHIS = {
    "Dvitiya",
    "Tritiya",
    "Panchami",
    "Shashthi",
    "Dashami",
    "Ekadashi",
    "Trayodashi",
    "Chaturdashi",
}

# Benefic Yogas (exclude inauspicious)
BENEFIC_YOGAS = {
    "Preeti", "Ayushman", "Saubhagya", "Shobhana", "Sukarma",
    "Dhriti", "Vriddhi", "Dhruva", "Harshana", "Vajra",
    "Siddhi", "Variyana", "Shiva", "Siddha", "Sadhya",
    "Shubha", "Shukla", "Brahma", "Indra",
}

# Benefic Karanas (Vishti is generally inauspicious)
BENEFIC_KARANAS = {
    "Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija",
}

# Benefic Lagnas (reuse benefic rashis for simplicity)
BENEFIC_LAGNAS = BENEFIC_RASHIS

# Benefic Jupiter placements (reuse benefic rashis)
BENEFIC_JUPITER_RASHIS = BENEFIC_RASHIS

# Benefic Dasha lords (simple heuristic)
BENEFIC_DASHA_LORDS = {"Jupiter", "Venus", "Mercury", "Moon"}

# Rahu Kalam timings (weekday → (start, end) in hours)
RAHU_KALAM = {
    0: (7.5, 9.0),
    1: (15.0, 16.5),
    2: (12.0, 13.5),
    3: (13.5, 15.0),
    4: (10.5, 12.0),
    5: (9.0, 10.5),
    6: (16.5, 18.0),
}

# Weights (easy tuning later)
WEIGHTS = {
    "nakshatra": 3,
    "rashi": 2,
    "pada": 1,
    "tithi": 2,
    "yoga": 2,
    "karana": 1,
    "lagna": 2,
    "eighth_house": 2,
    "jupiter": 2,
    "dasha": 2,
    "parents_dasha": 2,
    "lagna_friendship": 3,
    "arrival_indicator": 3,
    "dasha_sandhi": 2,
    "jupiter_compensation": 2,
    "dasha_clash": 3,
    "ninth_house_strength": 2,
    "fourth_house_strength": 2,
    "baby_start_dasha": 2
}

# Trait options parents can select
TRAIT_OPTIONS = [
    "health",
    "intelligence",
    "wealth",
    "leadership",
    "spiritual",
    "creativity",
    "stability",
    "compassion",
    "courage",
]

# Priority multipliers (primary, secondary, tertiary)
TRAIT_PRIORITY_MULTIPLIERS = [3, 2, 1]

# Trait -> weight deltas per astro factor
TRAIT_WEIGHT_OVERRIDES = {
    "health": {"lagna": 2, "tithi": 1},
    "intelligence": {"yoga": 2, "nakshatra": 1},
    "wealth": {"rashi": 2, "karana": 1},
    "leadership": {"lagna": 2, "nakshatra": 1},
    "spiritual": {"tithi": 2, "yoga": 1},
    "creativity": {"nakshatra": 1, "rashi": 1},
    "stability": {"rashi": 1, "lagna": 1},
    "compassion": {"nakshatra": 1, "tithi": 1},
    "courage": {"lagna": 2, "karana": 1},
}
