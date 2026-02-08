import os
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

import requests
from requests import HTTPError
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ----------------------------
# CONFIG (no hardcoding)
# ----------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
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


# ----------------------------
# HELPERS
# ----------------------------
def _date_bounds(years_back: int = 30, years_forward: int = 1):
    """Dynamic bounds for date inputs (prevents Streamlit min/max errors)."""
    today = date.today()
    min_d = today - timedelta(days=365 * years_back)
    max_d = today + timedelta(days=365 * years_forward)
    return min_d, max_d


def time_text_input(label: str, key: str, default: str = "00:00") -> str:
    """
    Returns a validated HH:MM string. If invalid, falls back to default and shows a warning.
    """
    val = st.text_input(label, value=default, key=key).strip()
    if re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", val):
        return val
    if val:
        st.warning(f"{label} must be in HH:MM (24-hour) format. Using {default}.")
    return default


def build_location_payload(prefix: str, title: str = "Location") -> Dict[str, Any]:
    """
    Returns:
      {"latitude": .., "longitude": .., "timezone": "..."}
    """
    st.subheader(title)
    mode = st.radio(
        "Choose location input mode",
        ["Place (city/state/country)", "Lat/Lon (manual)"],
        index=0,
        key=f"{prefix}_loc_mode",
        horizontal=True,
    )

    if mode == "Place (city/state/country)":
        place = st.text_input(
            "Place (City, State, Country) - optional if you fill fields below",
            value="",
            key=f"{prefix}_place",
        ).strip()
        c1, c2, c3 = st.columns(3)
        with c1:
            city = st.text_input("City", value="", key=f"{prefix}_city").strip()
        with c2:
            state = st.text_input("State", value="", key=f"{prefix}_state").strip()
        with c3:
            country = st.text_input("Country", value="", key=f"{prefix}_country").strip()

        tz = st.text_input(
            "Timezone (optional, auto-detected if empty)",
            value="",
            key=f"{prefix}_tz_place",
        ).strip()
        use_llm = st.checkbox(
            "Use LLM to normalize place text",
            value=False,
            key=f"{prefix}_use_llm",
        )

        payload = {
            "place": place or None,
            "city": city or None,
            "state": state or None,
            "country": country or None,
            "use_llm": bool(use_llm),
        }
        if tz:
            payload["timezone"] = tz
        return payload

    # Lat/Lon manual
    col1, col2 = st.columns(2)
    with col1:
        lat = st.number_input(
            "Latitude",
            value=28.6139,
            format="%.6f",
            key=f"{prefix}_lat",
        )
    with col2:
        lon = st.number_input(
            "Longitude",
            value=77.2090,
            format="%.6f",
            key=f"{prefix}_lon",
        )

    tz = st.text_input(
        "Timezone (optional, auto-detected if empty)",
        value="",
        key=f"{prefix}_tz_latlon",
    ).strip()

    payload = {"latitude": float(lat), "longitude": float(lon)}
    if tz:
        payload["timezone"] = tz
    return payload


def build_parent_payload(prefix: str, label: str) -> Dict[str, Any]:
    st.subheader(f"{label} Details")
    name = st.text_input(f"{label} Name", value="", key=f"{prefix}_name").strip()

    c1, c2 = st.columns([1, 1])
    with c1:
        min_pd, max_pd = _date_bounds(years_back=120, years_forward=1)
        dob = st.date_input(
            f"{label} Date of Birth",
            value=date.today(),
            min_value=min_pd,
            max_value=max_pd,
            key=f"{prefix}_dob",
        )
    with c2:
        tob = time_text_input(
            f"{label} Time of Birth (HH:MM)",
            key=f"{prefix}_tob",
            default="00:00",
        )

    location = build_location_payload(prefix=f"{prefix}_loc", title=f"{label} Location")

    return {
        "name": name,
        "date_of_birth": dob.isoformat(),
        "time_of_birth": tob,
        "location": location,
    }


def build_qualities_block(prefix: str) -> Dict[str, Any]:
    st.subheader("Desired Qualities")
    qualities_text = st.text_area(
        "Describe the qualities you want (free text)",
        value="",
        key=f"{prefix}_qualities_text",
        height=90,
    ).strip()
    qualities_selected = st.multiselect(
        "Select qualities (optional)",
        TRAIT_OPTIONS,
        default=[],
        key=f"{prefix}_qualities_selected",
    )
    qualities_priority = st.multiselect(
        "Priority order (pick up to 3, in order)",
        TRAIT_OPTIONS,
        default=[],
        key=f"{prefix}_qualities_priority",
        max_selections=3,
    )
    return {
        "qualities_text": qualities_text or None,
        "qualities_selected": qualities_selected or None,
        "qualities_priority": qualities_priority or None,
    }


def api_post(path: str, payload: Dict[str, Any], timeout_sec: int = 120) -> Dict[str, Any]:
    url = f"{API_BASE_URL}{path}"
    r = requests.post(url, json=payload, timeout=timeout_sec)
    try:
        r.raise_for_status()
    except HTTPError as e:
        # Include response body to surface FastAPI validation details (e.g., 422)
        detail = ""
        try:
            detail = r.text
        except Exception:
            detail = ""
        raise HTTPError(f"{e} | Response: {detail}") from e
    return r.json()

def nice_error(e: Exception) -> str:
    return str(e)


# ----------------------------
# PAGE
# ----------------------------
st.set_page_config(page_title="Baby Name + Muhurat MVP", layout="wide")
st.title("👶 Baby Name + Muhurat MVP (Localhost)")

st.caption(f"Backend API: {API_BASE_URL}")

tab_muhurat, tab_names = st.tabs(["🕉️ Muhurat (Baby not born)", "🧿 Baby Names (Baby born)"])


# ============================
# TAB 1: MUHURAT
# ============================
with tab_muhurat:
    st.header("🕉️ Suggest Auspicious Date/Time (Muhurat)")

    min_d, max_d = _date_bounds(years_back=5, years_forward=1)

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        start_d = st.date_input(
            "Start Date",
            value=date.today(),
            min_value=min_d,
            max_value=max_d,
            key="muhurat_start_date",
        )
    with c2:
        end_d = st.date_input(
            "End Date",
            value=date.today() + timedelta(days=3),
            min_value=min_d,
            max_value=max_d,
            key="muhurat_end_date",
        )
    with c3:
        max_results = st.selectbox(
            "Number of results",
            options=[5, 10, 15, 20, 30, 50],
            index=1,
            key="muhurat_max_results",
        )

    if end_d < start_d:
        st.warning("End Date should be >= Start Date.")

    location = build_location_payload(prefix="muhurat", title="Location")
    st.divider()
    st.subheader("Parents Details")
    mother = build_parent_payload(prefix="muhurat_mother", label="Mother")
    father = build_parent_payload(prefix="muhurat_father", label="Father")
    parents_payload = {"mother": mother, "father": father}
    if not mother["name"] or not father["name"]:
        st.warning("Please fill both parents' names to include parents in scoring.")
    st.divider()
    qualities_block = build_qualities_block(prefix="muhurat")

    payload = {
        "start_date": start_d.isoformat(),
        "end_date": end_d.isoformat(),
        "location": location,
        "max_results": int(max_results),
        "parents": parents_payload,
        **qualities_block,
    }

    st.divider()
    colA, colB = st.columns([1, 1])
    with colA:
        st.subheader("Request payload")
        st.json(payload)

    with colB:
        st.subheader("Actions")
        run = st.button("🔮 Suggest Muhurat", type="primary", use_container_width=True)

    if run and end_d >= start_d:
        try:
            with st.spinner("Calculating muhurat..."):
                data = api_post("/api/v1/muhurat/suggest", payload)
            st.success("Done ✅")

            results = data.get("results", [])
            if not results:
                st.info("No muhurat found in this range (based on current scoring/filters).")
            else:
                st.subheader("Results")
                st.dataframe(results, use_container_width=True)

                best = results[0]
                st.markdown(
                    f"### Best Pick\n"
                    f"**Date:** {best['date']}  \n"
                    f"**Time:** {best['time']}  \n"
                    f"**Nakshatra:** {best['nakshatra']} (Pada {best['pada']})  \n"
                    f"**Rashi:** {best['rashi']}  \n"
                    f"**Tithi:** {best['tithi']}  \n"
                    f"**Yoga:** {best['yoga']}  \n"
                    f"**Karana:** {best['karana']}  \n"
                    f"**Lagna:** {best['lagna']}  \n"
                    f"**8th House:** {best['eighth_house_rashi']}  \n"
                    f"**Jupiter:** {best['jupiter_rashi']}  \n"
                    f"**Dasha Lord:** {best['dasha_lord']}  \n"
                    f"**Score:** {best['score']}"
                )

        except Exception as e:
            st.error(f"API error: {nice_error(e)}")


# ============================
# TAB 2: BABY NAMES (placeholder now)
# ============================
with tab_names:
    st.header("🧿 Baby Name Suggestion (Baby born)")
    st.info("Next step: We’ll connect this tab to POST /api/v1/names/suggest. For now we’ll only collect inputs and show payload.")

    min_d2, max_d2 = _date_bounds(years_back=80, years_forward=0)

    st.subheader("Baby Details")
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        gender = st.selectbox("Gender", ["male", "female", "neutral"], key="names_gender")
    with c2:
        dob = st.date_input(
            "Date of Birth",
            value=date.today(),
            min_value=min_d2,
            max_value=date.today(),
            key="names_dob",
        )
    with c3:
        tob = time_text_input("Time of Birth (HH:MM)", key="names_tob", default="00:00")

    baby_location = build_location_payload(prefix="baby", title="Baby Location")
    st.divider()
    st.subheader("Parents Details")
    mother2 = build_parent_payload(prefix="names_mother", label="Mother")
    father2 = build_parent_payload(prefix="names_father", label="Father")
    parents_payload2 = {"mother": mother2, "father": father2}
    if not mother2["name"] or not father2["name"]:
        st.warning("Please fill both parents' names to include parents in payload.")
    st.divider()
    qualities_block2 = build_qualities_block(prefix="names")

    st.subheader("Preferences")
    c4, c5, c6 = st.columns([1, 1, 1])
    with c4:
        starting_letters = st.text_input(
            "Starting letters (comma separated)",
            value="",
            key="names_starting_letters",
        )
    with c5:
        name_length = st.selectbox(
            "Name length",
            ["any", "short", "medium", "long"],
            index=0,
            key="names_len",
        )
    with c6:
        count = st.selectbox("Suggestions", [5, 10, 15, 20], index=1, key="names_count")

    origins = st.multiselect(
        "Name origin/language",
        ["sanskrit", "hindi", "modern_indian", "traditional", "contemporary"],
        default=["sanskrit"],
        key="names_origins",
    )

    payload_names = {
        "baby_details": {
            "gender": gender,
            "date_of_birth": dob.isoformat(),
            "time_of_birth": tob,
            "location": baby_location,
        },
        "parents": parents_payload2,
        **qualities_block2,
        "preferences": {
            "starting_letters": [x.strip() for x in starting_letters.split(",") if x.strip()],
            "origins": origins,
            "name_length": name_length,
            "number_of_suggestions": int(count),
        },
    }

    st.divider()
    st.subheader("Name Suggest payload (preview)")
    st.json(payload_names)

    st.button("🧿 Suggest Names (next step)", disabled=True, use_container_width=True)
