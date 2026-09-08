import pandas as pd

OUTPUT_CSV = "imbl_boundary.csv"

# Official sequential coordinate points defining the India-Sri Lanka IMBL
# Derived from published MEA/UNCLOS Gazette agreements (Palk Strait & Gulf of Mannar)
imbl_points = [
    # Palk Strait Section (1974 Agreement)
    {"boundary_name": "India-Sri Lanka IMBL", "sequence_no": 1, "lat": 10.0833, "lon": 79.8500},
    {"boundary_name": "India-Sri Lanka IMBL", "sequence_no": 2, "lat": 10.0500, "lon": 79.8000},
    {"boundary_name": "India-Sri Lanka IMBL", "sequence_no": 3, "lat": 9.6833, "lon": 79.5333},
    {"boundary_name": "India-Sri Lanka IMBL", "sequence_no": 4, "lat": 9.3639, "lon": 79.3789},
    {"boundary_name": "India-Sri Lanka IMBL", "sequence_no": 5, "lat": 9.3653, "lon": 79.3361},
    {"boundary_name": "India-Sri Lanka IMBL", "sequence_no": 6, "lat": 9.2917, "lon": 79.2500},
    
    # Gulf of Mannar Section (1976 Agreement)
    {"boundary_name": "India-Sri Lanka IMBL", "sequence_no": 7, "lat": 9.1000, "lon": 79.2167},
    {"boundary_name": "India-Sri Lanka IMBL", "sequence_no": 8, "lat": 8.8833, "lon": 78.9167},
    {"boundary_name": "India-Sri Lanka IMBL", "sequence_no": 9, "lat": 8.6333, "lon": 78.6333},
    {"boundary_name": "India-Sri Lanka IMBL", "sequence_no": 10, "lat": 8.3667, "lon": 78.4167},
    {"boundary_name": "India-Sri Lanka IMBL", "sequence_no": 11, "lat": 7.9667, "lon": 78.0333},
    {"boundary_name": "India-Sri Lanka IMBL", "sequence_no": 12, "lat": 7.3333, "lon": 77.5833},
    {"boundary_name": "India-Sri Lanka IMBL", "sequence_no": 13, "lat": 6.0000, "lon": 76.6667},
    
    # India - Sri Lanka - Maldives Trijunction Point (Point T)
    {"boundary_name": "India-Sri Lanka IMBL", "sequence_no": 14, "lat": 4.7833, "lon": 75.5000}
]

# Convert to DataFrame
df = pd.DataFrame(imbl_points)

# Enforce exact target column order
target_columns = ["boundary_name", "sequence_no", "lat", "lon"]
df = df[target_columns]

# Save to CSV
df.to_csv(OUTPUT_CSV, index=False)

print(f"SUCCESS: Created {OUTPUT_CSV} with {len(df)} sequential boundary points!")
