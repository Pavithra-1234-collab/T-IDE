import numpy as np
import pandas as pd
import xarray as xr
import copernicusmarine

# Near-Real-Time (NRT) dataset ID
DATASET_ID = "cmems_obs-wind_glo_phy_nrt_l4_0.125deg_PT1H"

START_DATE = "2026-09-01T00:00:00"
END_DATE = "2026-09-02T00:00:00"

MIN_LAT, MAX_LAT = 13.0, 16.0
MIN_LON, MAX_LON = 73.0, 81.0

print("Fetching marine wind dataset (Near-Real-Time)...")

# Only request variables that exist in this product
ds = copernicusmarine.open_dataset(
    dataset_id=DATASET_ID,
    variables=["eastward_wind", "northward_wind"],
    start_datetime=START_DATE,
    end_datetime=END_DATE,
    minimum_latitude=MIN_LAT,
    maximum_latitude=MAX_LAT,
    minimum_longitude=MIN_LON,
    maximum_longitude=MAX_LON,
)

u = ds["eastward_wind"]
v = ds["northward_wind"]

# Calculate Wind Speed (m/s -> km/h) and Meteorological Wind Direction (deg)
speed_ms = np.sqrt(u**2 + v**2)
speed_kmh = speed_ms * 3.6
dir_deg = (270 - np.arctan2(v, u) * (180 / np.pi)) % 360

# Calculate estimated gust speed (standard meteorological factor ~1.35x)
gust_kmh = speed_kmh * 1.35

df = ds.to_dataframe().reset_index()

df["wind_speed_kmh"] = speed_kmh.values.flatten().round(2)
df["wind_direction_deg"] = dir_deg.values.flatten().round(1)
df["gust_speed_kmh"] = gust_kmh.values.flatten().round(2)
df["timestamp"] = pd.to_datetime(df["time"]).dt.strftime("%Y-%m-%dT%H:%M:%SZ")

target_df = df[
    [
        "latitude",
        "longitude",
        "timestamp",
        "wind_speed_kmh",
        "wind_direction_deg",
        "gust_speed_kmh",
    ]
].rename(columns={"latitude": "lat", "longitude": "lon"})

output_path = "wind.csv"
target_df.dropna().to_csv(output_path, index=False)
print(f"SUCCESS: Dataset generated and saved to {output_path}")