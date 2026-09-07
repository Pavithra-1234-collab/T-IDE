import pandas as pd

# Direct NOAA IBTrACS dataset for the North Indian Ocean (NI)
IBTRACS_URL = "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.NI.list.v04r01.csv"
OUTPUT_CSV = "cyclone_alerts_training_large.csv"

print("1. Downloading historical cyclone tracks from NOAA IBTrACS...")

# Read CSV, skipping the units header row (row 1)
df = pd.read_csv(IBTRACS_URL, skiprows=[1], low_memory=False)

print("2. Processing and mapping fields to target schema...")

# Filter out records missing critical location or wind data
df = df.dropna(subset=["LAT", "LON", "USA_WIND"])

# Map wind speed from Knots to KM/H (1 Knot = 1.852 KM/H)
df["wind_speed_at_center_kmh"] = (
    pd.to_numeric(df["USA_WIND"], errors="coerce") * 1.852
).round(1)

# Helper function to classify severity levels based on wind speed (IMD scale)
def classify_severity(wind_kmh):
    if wind_kmh < 62:
        return "Depression"
    elif wind_kmh < 88:
        return "Cyclonic Storm"
    elif wind_kmh < 117:
        return "Severe Cyclonic Storm"
    elif wind_kmh < 166:
        return "Very Severe Cyclonic Storm"
    elif wind_kmh < 221:
        return "Extremely Severe Cyclonic Storm"
    else:
        return "Super Cyclonic Storm"

df["severity_level"] = df["wind_speed_at_center_kmh"].apply(classify_severity)

# Column mapping
df["alert_id"] = "IBTRACS-" + df["SID"].astype(str)
df["alert_type"] = "Cyclone Warning"
df["center_lat"] = pd.to_numeric(df["LAT"], errors="coerce").round(2)
df["center_lon"] = pd.to_numeric(df["LON"], errors="coerce").round(2)
df["radius_km"] = 150.0  # Standard storm radius baseline
df["issued_at"] = pd.to_datetime(df["ISO_TIME"]).dt.strftime(
    "%Y-%m-%dT%H:%M:%SZ"
)

# Calculate expires_at (default +24 hours from observation)
df["expires_at"] = (
    pd.to_datetime(df["ISO_TIME"]) + pd.Timedelta(hours=24)
).dt.strftime("%Y-%m-%dT%H:%M:%SZ")

df["source_agency"] = "NOAA_IBTrACS"

# Target schema alignment
target_columns = [
    "alert_id",
    "alert_type",
    "center_lat",
    "center_lon",
    "radius_km",
    "severity_level",
    "wind_speed_at_center_kmh",
    "issued_at",
    "expires_at",
    "source_agency",
]

clean_df = df[target_columns].dropna()

# Save complete training set
clean_df.to_csv(OUTPUT_CSV, index=False)

print(
    f"SUCCESS: Generated {len(clean_df)} historical training rows in {OUTPUT_CSV}!"
)