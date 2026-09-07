import os
import numpy as np
import pandas as pd
import xarray as xr
import copernicusmarine

# Active Copernicus Physics Current Dataset
DATASET_ID = "cmems_mod_glo_phy_anfc_merged-uv_PT1H-i"

START_DATE = "2026-09-01T00:00:00"
END_DATE = "2026-09-02T00:00:00"
MIN_LAT, MAX_LAT = 13.0, 16.0
MIN_LON, MAX_LON = 73.0, 81.0

TEMP_FILE = "temp_currents.nc"
OUTPUT_CSV = "currents.csv"

print("1. Subsetting ocean currents dataset via Copernicus API...")

copernicusmarine.subset(
    dataset_id=DATASET_ID,
    variables=["uo", "vo"],
    start_datetime=START_DATE,
    end_datetime=END_DATE,
    minimum_latitude=MIN_LAT,
    maximum_latitude=MAX_LAT,
    minimum_longitude=MIN_LON,
    maximum_longitude=MAX_LON,
    output_filename=TEMP_FILE,
)

print("2. Converting vector components to speed & direction...")

ds = xr.open_dataset(TEMP_FILE)

# Select surface layer (depth=0) if multi-depth levels exist
if "depth" in ds.coords or "depth" in ds.dims:
    ds = ds.isel(depth=0)

df = ds.to_dataframe().reset_index()

# Extract zonal (uo) and meridional (vo) velocities
u = df["uo"]
v = df["vo"]

# Compute speed (m/s) and oceanographic direction (degrees)
df["current_speed_ms"] = np.sqrt(u**2 + v**2).round(2)
df["current_direction_deg"] = (np.degrees(np.arctan2(u, v)) % 360).round(1)

# Format ISO timestamp
df["timestamp"] = pd.to_datetime(df["time"]).dt.strftime("%Y-%m-%dT%H:%M:%SZ")

# Map to requested target column order: lat, lon, timestamp, current_speed_ms, current_direction_deg
target_df = df[
    [
        "latitude",
        "longitude",
        "timestamp",
        "current_speed_ms",
        "current_direction_deg",
    ]
].rename(
    columns={
        "latitude": "lat",
        "longitude": "lon",
    }
)

# Export clean CSV
target_df.dropna().to_csv(OUTPUT_CSV, index=False)
ds.close()

# Cleanup temporary NetCDF
if os.path.exists(TEMP_FILE):
    os.remove(TEMP_FILE)

print(f"SUCCESS: Exported clean dataset to {OUTPUT_CSV}!")