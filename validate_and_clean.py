import os
import pandas as pd

# 1. Target Schemas Definition
EXPECTED_SCHEMAS = {
    "sst.csv": [
        "lat",
        "lon",
        "date",
        "sst_value_celsius",
        "source_satellite",
        "quality_flag",
    ],
    "chlorophyll.csv": [
        "lat",
        "lon",
        "date",
        "chlorophyll_a_mg_m3",
        "source_satellite",
        "quality_flag",
    ],
    "pfz_zones.csv": [
        "zone_id",
        "lat",
        "lon",
        "date_issued",
        "valid_until",
        "radius_km",
        "confidence_score",
    ],
    "wind.csv": [
        "lat",
        "lon",
        "timestamp",
        "wind_speed_kmh",
        "wind_direction_deg",
        "gust_speed_kmh",
    ],
    "waves.csv": [
        "lat",
        "lon",
        "timestamp",
        "significant_wave_height_m",
        "wave_period_s",
        "swell_height_m",
        "swell_direction_deg",
    ],
    "currents.csv": [
        "lat",
        "lon",
        "timestamp",
        "current_speed_ms",
        "current_direction_deg",
    ],
    "tides.csv": [
        "port_name",
        "date",
        "high_tide_time",
        "high_tide_height_m",
        "low_tide_time",
        "low_tide_height_m",
    ],
    "cyclone_alerts.csv": [
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
    ],
    "imbl_boundary.csv": ["boundary_name", "sequence_no", "lat", "lon"],
    "mpa_zones.csv": [
        "zone_name",
        "sequence_no",
        "lat",
        "lon",
        "restriction_type",
    ],
    "vessel_profiles.csv": [
        "vessel_id",
        "user_id",
        "vessel_size_class",
        "home_port",
        "registered_language",
        "current_lat",
        "current_lon",
        "last_updated_timestamp",
        "contact_number",
    ],
    "catch_reports.csv": [
        "report_id",
        "user_id",
        "lat",
        "lon",
        "date",
        "catch_outcome",
        "species",
        "free_text_note",
    ],
}

# Output directory for clean production data
PROCESSED_DIR = "processed_data"
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Demo Geographic Bounding Box (Tamil Nadu / South Indian Coastline)
MIN_LAT, MAX_LAT = 4.0, 22.0
MIN_LON, MAX_LON = 72.0, 88.0

print("==================================================")
print("  STEP 1: VALIDATING & CLEANING PIPELINE DATASETS ")
print("==================================================\n")

for filename, expected_cols in EXPECTED_SCHEMAS.items():
    if not os.path.exists(filename):
        print(f"⚠ {filename}: FILE NOT FOUND (Skipping)")
        continue

    # Read CSV dataset
    df = pd.read_csv(filename)
    initial_rows = len(df)

    # A. Validate Schema & Reorder / Rename Columns
    actual_cols = list(df.columns)

    # Check for missing expected columns
    missing_cols = [col for col in expected_cols if col not in actual_cols]
    if missing_cols:
        print(
            f"❌ {filename}: Missing columns {missing_cols}. Adding defaults..."
        )
        for col in missing_cols:
            df[col] = None

    # Enforce precise column ordering
    df = df[expected_cols]

    # B. Step 2 Data Cleaning Rules
    # 1. Drop rows missing critical location/timestamp fields
    spatial_cols = [c for c in ["lat", "lon", "center_lat", "center_lon", "current_lat", "current_lon"] if c in df.columns]
    time_cols = [c for c in ["date", "timestamp", "issued_at", "date_issued"] if c in df.columns]
    critical_cols = spatial_cols + time_cols

    if critical_cols:
        df = df.dropna(subset=critical_cols)

    # 2. Filter data within demo geographic bounding box
    if "lat" in df.columns and "lon" in df.columns:
        df = df[
            (df["lat"] >= MIN_LAT)
            & (df["lat"] <= MAX_LAT)
            & (df["lon"] >= MIN_LON)
            & (df["lon"] <= MAX_LON)
        ]
    elif "center_lat" in df.columns and "center_lon" in df.columns:
        df = df[
            (df["center_lat"] >= MIN_LAT)
            & (df["center_lat"] <= MAX_LAT)
            & (df["center_lon"] >= MIN_LON)
            & (df["center_lon"] <= MAX_LON)
        ]

    # 3. Standardize timestamps to ISO 8601 format
    for t_col in time_cols:
        try:
            df[t_col] = pd.to_datetime(df[t_col]).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            pass

    # Save clean dataset into processed_data/ folder
    clean_path = os.path.join(PROCESSED_DIR, filename)
    df.to_csv(clean_path, index=False)

    print(f"✓ {filename}: CLEANED & VALIDATED")
    print(f"  Rows: {initial_rows} -> {len(df)} saved to '{clean_path}'")
    print(f"  Null Values: {df.isnull().sum().sum()}")
    print("-" * 50)

print(
    f"\nSUCCESS: All datasets cleaned and saved in '{PROCESSED_DIR}/'!"
)