import time
import pandas as pd
import requests
import urllib3

# Suppress SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_KEY = "d0a2727a-6f9a-4d66-b27a-1ea1ddd16f5e"
OUTPUT_CSV = "tides.csv"

PORTS = [
    {"name": "Marmagao", "lat": 15.41, "lon": 73.80},
    {"name": "New Mangalore", "lat": 12.92, "lon": 74.81},
    {"name": "Kochi", "lat": 9.96, "lon": 76.26},
    {"name": "Mumbai", "lat": 18.96, "lon": 72.84},
]

start_time = int(time.time())
length_seconds = 7 * 86400

all_port_rows = []

print("1. Querying WorldTides API...")

for port in PORTS:
    url = (
        f"https://www.worldtides.info/api/v3"
        f"?extremes"
        f"&lat={port['lat']}"
        f"&lon={port['lon']}"
        f"&start={start_time}"
        f"&length={length_seconds}"
        f"&datum=LAT"
        f"&key={API_KEY}"
    )

    # Added verify=False to bypass local SSL certificate verification
    response = requests.get(url, verify=False)

    if response.status_code != 200:
        print(f"Error fetching {port['name']}: {response.text}")
        continue

    data = response.json()
    extremes = data.get("extremes", [])

    if not extremes:
        print(f"Warning: No extreme events returned for {port['name']}.")
        continue

    daily_data = {}

    for item in extremes:
        dt = pd.to_datetime(item["dt"], unit="s")
        date_str = dt.strftime("%Y-%m-%d")
        time_str = dt.strftime("%H:%M")
        height_str = f"{item['height']:.2f}"
        tide_type = item["type"].lower()

        if date_str not in daily_data:
            daily_data[date_str] = {
                "high_time": [],
                "high_height": [],
                "low_time": [],
                "low_height": [],
            }

        if tide_type == "high":
            daily_data[date_str]["high_time"].append(time_str)
            daily_data[date_str]["high_height"].append(height_str)
        elif tide_type == "low":
            daily_data[date_str]["low_time"].append(time_str)
            daily_data[date_str]["low_height"].append(height_str)

    for date_str, tides in daily_data.items():
        all_port_rows.append(
            {
                "port_name": port["name"],
                "date": date_str,
                "high_tide_time": "; ".join(tides["high_time"]),
                "high_tide_height_m": "; ".join(tides["high_height"]),
                "low_tide_time": "; ".join(tides["low_time"]),
                "low_tide_height_m": "; ".join(tides["low_height"]),
            }
        )

# Export to CSV
df = pd.DataFrame(all_port_rows)

if not df.empty:
    target_columns = [
        "port_name",
        "date",
        "high_tide_time",
        "high_tide_height_m",
        "low_tide_time",
        "low_tide_height_m",
    ]
    df = df[target_columns]
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"SUCCESS: Generated {OUTPUT_CSV} with {len(df)} rows!")
else:
    print("API returned 0 rows. Check WorldTides dashboard settings.")