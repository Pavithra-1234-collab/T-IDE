import random
from datetime import datetime, timedelta
import pandas as pd

OUTPUT_CSV = "catch_reports.csv"
NUM_REPORTS = 40

# Realistic fishing ground clusters (off West & East Coasts of India)
FISHING_LOCATIONS = [
    {"name": "Off Goa Coast", "lat": 15.35, "lon": 73.65},
    {"name": "Mangalore Outer Waters", "lat": 12.85, "lon": 74.65},
    {"name": "Kochi Offshore", "lat": 9.90, "lon": 76.10},
    {"name": "Mumbai Offshore", "lat": 18.85, "lon": 72.65},
    {"name": "Palk Bay", "lat": 10.00, "lon": 79.50},
    {"name": "Vizag Coastal Waters", "lat": 17.60, "lon": 83.35},
]

SPECIES_LIST = [
    "Indian Mackerel (Rastrelliger kanagurta)",
    "Oil Sardine (Sardinella longiceps)",
    "Kingfish / Surmai (Scomberomorus commerson)",
    "Yellowfin Tuna (Thunnus albacares)",
    "Prawns / Shrimp (Penaeus monodon)",
    "Pomfret (Pampus argenteus)",
    "Cuttlefish (Sepia pharaonis)",
]

CATCH_OUTCOMES = ["High Catch", "Moderate Catch", "Low Catch", "Zero Catch"]

SAMPLE_NOTES = [
    "Good schools of mackerel spotted near ocean front.",
    "Strong currents made trawling difficult today.",
    "High wave activity; returned early to harbor.",
    "Water was unusually warm, fish found deeper.",
    "Heavy sardine catch using purse seine.",
    "Spotted large school near thermal boundary.",
    "Low yield due to rough seas.",
]

print(f"1. Generating {NUM_REPORTS} crowdsourced catch feedback records...")

records = []
now = datetime.utcnow()

for i in range(1, NUM_REPORTS + 1):
    report_id = f"REP-2026-{2000 + i}"
    user_id = f"USR-{5000 + random.randint(1, 50)}"

    # Select location and add coordinate offset for spatial spread
    loc = random.choice(FISHING_LOCATIONS)
    lat = round(loc["lat"] + random.uniform(-0.10, 0.10), 4)
    lon = round(loc["lon"] + random.uniform(-0.10, 0.10), 4)

    # Random date within the last 14 days
    date_offset = random.randint(0, 14)
    report_date = (now - timedelta(days=date_offset)).strftime("%Y-%m-%d")

    outcome = random.choice(CATCH_OUTCOMES)
    species = random.choice(SPECIES_LIST) if outcome != "Zero Catch" else "None"
    note = (
        random.choice(SAMPLE_NOTES)
        if outcome != "Zero Catch"
        else "No fish activity observed in this sector."
    )

    records.append(
        {
            "report_id": report_id,
            "user_id": user_id,
            "lat": lat,
            "lon": lon,
            "date": report_date,
            "catch_outcome": outcome,
            "species": species,
            "free_text_note": note,
        }
    )

# Format into DataFrame with exact required column order
df = pd.DataFrame(records)

target_columns = [
    "report_id",
    "user_id",
    "lat",
    "lon",
    "date",
    "catch_outcome",
    "species",
    "free_text_note",
]

df = df[target_columns]
df.to_csv(OUTPUT_CSV, index=False)

print(
    f"SUCCESS: Generated {OUTPUT_CSV} with {len(df)} crowdsourced test records!"
)