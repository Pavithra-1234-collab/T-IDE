from uuid import uuid4
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

try:
    from orca_pipeline import run_orca_pipeline
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from orca_pipeline import run_orca_pipeline

try:
    from .db import engine
    from .models import CatchReport, QueryRequest
except ImportError:
    from db import engine
    from models import CatchReport, QueryRequest


app = FastAPI(title="ORCA API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/pfz/nearest")
def nearest_pfz(lat: float, lon: float):
    query = text(
        """
        SELECT
            zone_id,
            ST_Y(location::geometry) AS lat,
            ST_X(location::geometry) AS lon,
            radius_km,
            confidence_score,
            ST_Distance(
                location,
                ST_MakePoint(:lon, :lat)::geography
            ) / 1000 AS distance_km
        FROM pfz_zones
        ORDER BY location <-> ST_MakePoint(:lon, :lat)::geography
        LIMIT 1
        """
    )
    with engine.connect() as connection:
        row = connection.execute(query, {"lat": lat, "lon": lon}).mappings().first()
    return dict(row) if row else None


@app.get("/alerts/nearby")
def nearby_alerts(lat: float, lon: float, radius_km: float = 50):
    query = text(
        """
        SELECT *
        FROM cyclone_alerts
        WHERE expires_at > NOW()
          AND ST_DWithin(
              location,
              ST_MakePoint(:lon, :lat)::geography,
              :radius_m
          )
        ORDER BY ST_Distance(location, ST_MakePoint(:lon, :lat)::geography)
        """
    )
    parameters = {"lat": lat, "lon": lon, "radius_m": radius_km * 1000}
    with engine.connect() as connection:
        rows = connection.execute(query, parameters).mappings().all()
    return [dict(row) for row in rows]


@app.get("/conditions")
def conditions(lat: float, lon: float, date: str):
    wind_query = text(
        """
        SELECT
            wind_speed_kmh,
            wind_direction_deg,
            ST_Distance(location, ST_MakePoint(:lon, :lat)::geography) AS distance_m
        FROM wind_readings
        WHERE reading_timestamp::date = :date
        ORDER BY location <-> ST_MakePoint(:lon, :lat)::geography
        LIMIT 1
        """
    )
    wave_query = text(
        """
        SELECT
            significant_wave_height_m,
            wave_period_s,
            ST_Distance(location, ST_MakePoint(:lon, :lat)::geography) AS distance_m
        FROM wave_readings
        WHERE reading_timestamp::date = :date
        ORDER BY location <-> ST_MakePoint(:lon, :lat)::geography
        LIMIT 1
        """
    )
    parameters = {"lat": lat, "lon": lon, "date": date}
    with engine.connect() as connection:
        wind = connection.execute(wind_query, parameters).mappings().first()
        wave = connection.execute(wave_query, parameters).mappings().first()
    return {
        "wind": dict(wind) if wind else None,
        "wave": dict(wave) if wave else None,
    }


@app.get("/zones/favourable")
def favourable_zones(
    lat: float,
    lon: float,
    date: str,
    radius_km: float = 100,
):
    query = text(
        """
        SELECT
            c.zone_id,
            ST_Y(c.location::geometry) AS lat,
            ST_X(c.location::geometry) AS lon,
            c.chlorophyll_a_mg_m3,
            s.sst_celsius,
            ST_Distance(
                c.location,
                ST_MakePoint(:lon, :lat)::geography
            ) / 1000 AS distance_km
        FROM chlorophyll_readings c
        JOIN sst_readings s
          ON ST_DWithin(c.location, s.location, 1000)
         AND c.reading_date = s.reading_date
        WHERE c.reading_date = :date
          AND c.chlorophyll_a_mg_m3 > 0.5
          AND ST_DWithin(
              c.location,
              ST_MakePoint(:lon, :lat)::geography,
              :radius_m
          )
        ORDER BY c.chlorophyll_a_mg_m3 DESC
        LIMIT 5
        """
    )
    parameters = {"lat": lat, "lon": lon, "date": date, "radius_m": radius_km * 1000}
    with engine.connect() as connection:
        rows = connection.execute(query, parameters).mappings().all()
    return [dict(row) for row in rows]


@app.get("/hazards/nearby")
def nearby_hazards(lat: float, lon: float):
    imbl_query = text(
        """
        SELECT
            ST_Distance(
                boundary,
                ST_MakePoint(:lon, :lat)::geography
            ) / 1000 AS distance_km
        FROM imbl_boundary
        ORDER BY boundary <-> ST_MakePoint(:lon, :lat)::geography
        LIMIT 1
        """
    )
    mpa_query = text(
        """
        SELECT zone_name, restriction_type
        FROM mpa_zones
        WHERE ST_DWithin(
            location,
            ST_MakePoint(:lon, :lat)::geography,
            5000
        )
        ORDER BY ST_Distance(location, ST_MakePoint(:lon, :lat)::geography)
        """
    )
    parameters = {"lat": lat, "lon": lon}
    with engine.connect() as connection:
        imbl = connection.execute(imbl_query, parameters).mappings().first()
        mpa_rows = connection.execute(mpa_query, parameters).mappings().all()
    return {
        "imbl_boundary": dict(imbl) if imbl else None,
        "mpa_zones": [dict(row) for row in mpa_rows],
    }


@app.post("/catch-report")
def create_catch_report(payload: CatchReport):
    report_id = str(uuid4())
    query = text(
        """
        INSERT INTO catch_reports (
            report_id,
            user_id,
            location,
            date,
            catch_outcome,
            species,
            free_text_note
        )
        VALUES (
            :report_id,
            :user_id,
            ST_MakePoint(:lon, :lat)::geography,
            :date,
            :catch_outcome,
            :species,
            :free_text_note
        )
        """
    )
    parameters = {
        "report_id": report_id,
        "user_id": payload.user_id,
        "lat": payload.lat,
        "lon": payload.lon,
        "date": payload.date,
        "catch_outcome": payload.catch_outcome,
        "species": payload.species,
        "free_text_note": payload.free_text_note,
    }
    with engine.begin() as connection:
        connection.execute(query, parameters)
    return {"status": "recorded"}


@app.post("/query")
async def query_agent(payload: QueryRequest):
    return await run_orca_pipeline(
        query_text=payload.query,
        lat=payload.lat,
        lon=payload.lon,
        date=payload.date,
    )


__all__ = ["app"]
