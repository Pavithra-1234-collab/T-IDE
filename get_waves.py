import os
import pandas as pd
import xarray as xr
import copernicusmarine

# Active dataset ID in Copernicus Marine Data Store
DATASET_ID = "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"

START_DATE = "2026-09-01T00:00:00"
END_DATE = "2026-09-02T00:00:00"
MIN_LAT, MAX_LAT = 13.0, 16.0
MIN_LON, MAX_LON = 73.0, 81.0

TEMP_FILE = "temp_waves.nc"
OUTPUT_CSV = "waves.csv"

print("1. Querying Copernicus Marine API...")

copernicusmarine.subset(
    dataset_id=DATASET_ID,
    variables=["VHM0", "VTPK", "VHM0_SW1", "VMDR_SW1"],
    start_datetime=START_DATE,
    end_datetime=END_DATE,
    minimum_latitude=MIN_LAT,
    maximum_latitude=MAX_LAT,
    minimum_longitude=MIN_LON,
    maximum_longitude=MAX_LON,
    output_filename=TEMP_FILE,
)

print("2. Converting downloaded data to CSV...")

ds = xr.open_dataset(TEMP_FILE)
df = ds.to_dataframe().reset_index()

df["timestamp"] = pd.to_datetime(df["time"]).dt.strftime("%Y-%m-%dT%H:%M:%SZ")

target_df = df[
    [
        "latitude",
        "longitude",
        "timestamp",
        "VHM0",
        "VTPK",
        "VHM0_SW1",
        "VMDR_SW1",
    ]
].rename(
    columns={
        "latitude": "lat",
        "longitude": "lon",
        "VHM0": "significant_wave_height_m",
        "VTPK": "wave_period_s",
        "VHM0_SW1": "swell_height_m",
        "VMDR_SW1": "swell_direction_deg",
    }
)

target_df["significant_wave_height_m"] = target_df["significant_wave_height_m"].round(2)
target_df["wave_period_s"] = target_df["wave_period_s"].round(1)
target_df["swell_height_m"] = target_df["swell_height_m"].round(2)
target_df["swell_direction_deg"] = target_df["swell_direction_deg"].round(1)

target_df.dropna().to_csv(OUTPUT_CSV, index=False)
ds.close()

if os.path.exists(TEMP_FILE):
    os.remove(TEMP_FILE)

print(f"SUCCESS: Created {OUTPUT_CSV} in your folder!")