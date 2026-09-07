import random
from datetime import datetime, timedelta
import pandas as pd

OUTPUT_CSV = "vessel_profiles.csv"

# Configuration for test data generation
NUM_VESSELS = 50

PORTS = [
    {"name": "Marmagao", "lat": 15.41, "lon": 73.80},
    {"name": "New Mangalore", "lat": 12.92, "lon": 74.81},
    {"name": "Kochi", "lat": 9.96, "lon": 76.26},
    {"name": "Mumbai", "lat": 18.96, "lon": 72.84},
    {"name": "Chennai", "lat": 13.08, "lon": 80.27},
    {"name": "Visakhapatnam", "lat": 17.68, "lon": 83.21},
]

SIZE_CLASSES = ["Small Non-Motorized", "Motorized Artisanal", "Mechanized Trawler", "Deep Sea Vessel"]
LANGUAGES = ["hi", "ta", "te", "ml", "kn", "mr", "gu", "bn"]

print(f"1. Generating {NUM_VESSELS} mock vessel profile records...")

records = []
now = datetime.utcnow()

for i in range(1, NUM_VESSELS + 1):
    vessel_id = f"IND-VES-{1000 + i}"
    user_id = f"USR-{5000 + i}"
    
    home_port_info = random.choice(PORTS)
    home_port = home_port_info["name"]
    
    # Add minor coordinate jitter around home port for live lat/lon simulation
    lat_jitter = random.uniform(-0.15, 0.15)
    lon_jitter = random.uniform(-0.15, 0.15)
    current_lat = round(home_port_info["lat"] + lat_jitter, 4)
    current_lon = round(home_port_info["lon"] + lon_jitter, 4)
    
    size_class = random.choice(SIZE_CLASSES)
    language = random.choice(LANGUAGES)
    
    # Generate timestamp within the last 12 hours
    random_minutes = random.randint(0, 720)
    last_updated = (now - timedelta(minutes=random_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Indian mobile number format
    contact_number = f"+91{random.randint(6000000000, 9999999999)}"
    
    records.append({
        "vessel_id": vessel_id,
        "user_id": user_id,
        "vessel_size_class": size_class,
        "home_port": home_port,
        "registered_language": language,
        "current_lat": current_lat,
        "current_lon": current_lon,
        "last_updated_timestamp": last_updated,
        "contact_number": contact_number
    })

# Format into DataFrame
df = pd.DataFrame(records)

# Enforce exact requested column order
target_columns = [
    "vessel_id",
    "user_id",
    "vessel_size_class",
    "home_port",
    "registered_language",
    "current_lat",
    "current_lon",
    "last_updated_timestamp",
    "contact_number"
]

df = df[target_columns]
df.to_csv(OUTPUT_CSV, index=False)

print(f"SUCCESS: Generated {OUTPUT_CSV} with {len(df)} records!")