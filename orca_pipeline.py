import asyncio
import json
import os
import time
from datetime import date as date_type
from datetime import datetime, timezone
from typing import Any

import anthropic
import copernicusmarine
import httpx


BASE_URL = "http://localhost:8000"
SPECIALIST_NAMES = [
    "marine_data_agent",
    "weather_agent",
    "ocean_agent",
    "pfz_agent",
    "geospatial_agent",
]


def call_llm(prompt: str) -> str:
    """Call Claude Sonnet and return its text response."""
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(
        block.text
        for block in response.content
        if getattr(block, "type", None) == "text"
    ).strip()


def _date_for_state(value: str | None) -> str:
    return value or datetime.now(timezone.utc).date().isoformat()


def _parse_json_object(value: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        start = value.find("{")
        end = value.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(value[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _agent_names_from_text(value: str) -> list[str]:
    lowered = value.lower()
    return [
        name
        for name in SPECIALIST_NAMES
        if name in lowered or name.removesuffix("_agent") in lowered
    ]


def _fallback_needed_agents(query: str) -> list[str]:
    lowered = query.lower()
    selected = []
    categories = {
        "weather_agent": ("weather", "wind", "cyclone", "alert", "storm"),
        "ocean_agent": ("tide", "wave", "current", "sea", "ocean", "sst"),
        "pfz_agent": ("pfz", "fish", "fishing", "catch", "favourable"),
        "geospatial_agent": ("hazard", "mpa", "imbl", "boundary", "route", "map"),
    }
    for agent_name, keywords in categories.items():
        if any(keyword in lowered for keyword in keywords):
            selected.append(agent_name)
    return selected or SPECIALIST_NAMES.copy()


async def _orchestrator_decision(state: dict[str, Any]) -> dict[str, Any]:
    prompt = f"""
You are the ORCA orchestrator. Identify which specialist agents are needed for this
marine safety query, then decide whether the currently collected evidence is enough.
Available agents: {', '.join(SPECIALIST_NAMES)}.
Return only JSON with this shape:
{{"needed_agents": ["agent_name"], "sufficient": false}}

Query: {state['query']}
Current evidence: {json.dumps(state.get('specialist_results', {}), default=str)}
"""
    try:
        raw = await asyncio.to_thread(call_llm, prompt)
        parsed = _parse_json_object(raw) or {}
    except Exception as error:
        parsed = {"error": str(error)}

    requested = parsed.get("needed_agents", [])
    if isinstance(requested, str):
        requested = _agent_names_from_text(requested)
    requested = [name for name in requested if name in SPECIALIST_NAMES]
    if not requested:
        requested = _fallback_needed_agents(state["query"])
    return {
        "needed_agents": requested,
        "sufficient": bool(parsed.get("sufficient", False)),
        "orchestrator_error": parsed.get("error"),
    }


async def orchestrator(state: dict[str, Any], max_iterations: int = 2) -> dict[str, Any]:
    """Select specialists and repeat the evidence check up to max_iterations times."""
    current = {**state, "specialist_results": dict(state.get("specialist_results", {}))}
    iterations = max(1, max_iterations)
    for iteration in range(iterations):
        decision = await _orchestrator_decision(current)
        current.update(decision)
        current["orchestrator_iteration"] = iteration + 1
        if decision["sufficient"] and current["specialist_results"]:
            break
        current["specialist_results"] = await _run_specialists(current)
    return current


async def _get_json(
    client: httpx.AsyncClient,
    path: str,
    params: dict[str, Any],
) -> Any:
    response = await client.get(f"{BASE_URL}{path}", params=params)
    response.raise_for_status()
    return response.json()


async def _safe_get(
    client: httpx.AsyncClient,
    name: str,
    path: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    try:
        return {name: await _get_json(client, path, params)}
    except Exception as error:
        return {name: {"error": str(error)}}


async def marine_data_agent(
    state: dict[str, Any], client: httpx.AsyncClient
) -> dict[str, Any]:
    params = {"lat": state["lat"], "lon": state["lon"], "date": state["date"]}
    conditions, hazards = await asyncio.gather(
        _safe_get(client, "conditions", "/conditions", params),
        _safe_get(client, "hazards", "/hazards/nearby", params),
    )
    return {"agent": "marine_data_agent", "data": {**conditions, **hazards}}


async def weather_agent(
    state: dict[str, Any], client: httpx.AsyncClient
) -> dict[str, Any]:
    params = {"lat": state["lat"], "lon": state["lon"]}
    alerts = await _safe_get(client, "alerts", "/alerts/nearby", params)
    return {"agent": "weather_agent", "data": alerts}


def _fetch_copernicus_ocean_data(state: dict[str, Any]) -> dict[str, Any]:
    """Fetch a small nearest-point ocean subset through the Copernicus SDK."""
    dataset_id = os.getenv(
        "COPERNICUS_DATASET_ID", "cmems_mod_glo_phy_anfc_0.083deg_P1D-m"
    )
    try:
        dataset = copernicusmarine.open_dataset(
            dataset_id=dataset_id,
            variables=["thetao"],
            start_datetime=f"{state['date']}T00:00:00",
            end_datetime=f"{state['date']}T23:59:59",
            minimum_latitude=state["lat"] - 0.1,
            maximum_latitude=state["lat"] + 0.1,
            minimum_longitude=state["lon"] - 0.1,
            maximum_longitude=state["lon"] + 0.1,
        )
        point = dataset.sel(
            latitude=state["lat"], longitude=state["lon"], method="nearest"
        )
        values = point["thetao"].values
        value = values.item() if getattr(values, "size", 0) == 1 else values.flat[0]
        dataset.close()
        return {"source": "copernicusmarine", "sst_celsius": float(value)}
    except Exception as error:
        return {"source": "copernicusmarine", "error": str(error)}


def _fetch_copernicus_wave_data(state: dict[str, Any]) -> dict[str, Any]:
    """Fetch the nearest Copernicus significant wave height value."""
    dataset_id = os.getenv(
        "COPERNICUS_WAVE_DATASET_ID", "cmems_mod_glo_wav_anfc_0.083deg_PT3H-i"
    )
    try:
        dataset = copernicusmarine.open_dataset(
            dataset_id=dataset_id,
            variables=["VHM0"],
            start_datetime=f"{state['date']}T00:00:00",
            end_datetime=f"{state['date']}T23:59:59",
            minimum_latitude=state["lat"] - 0.1,
            maximum_latitude=state["lat"] + 0.1,
            minimum_longitude=state["lon"] - 0.1,
            maximum_longitude=state["lon"] + 0.1,
        )
        point = dataset.sel(
            latitude=state["lat"], longitude=state["lon"], method="nearest"
        )
        values = point["VHM0"].values
        value = values.item() if getattr(values, "size", 0) == 1 else values.flat[0]
        dataset.close()
        return {"source": "copernicusmarine", "significant_wave_height_m": float(value)}
    except Exception as error:
        return {"source": "copernicusmarine", "error": str(error)}


async def _worldtides_30_day(state: dict[str, Any], client: httpx.AsyncClient) -> dict[str, Any]:
    api_key = os.getenv("WORLDTIDES_API_KEY")
    if not api_key:
        return {"source": "worldtides", "error": "WORLDTIDES_API_KEY is not configured"}
    try:
        response = await client.get(
            "https://www.worldtides.info/api/v3",
            params={
                "extremes": "",
                "lat": state["lat"],
                "lon": state["lon"],
                "start": int(time.time()),
                "length": 30 * 86400,
                "datum": "LAT",
                "key": api_key,
            },
        )
        response.raise_for_status()
        payload = response.json()
        return {"source": "worldtides", "extremes": payload.get("extremes", [])}
    except Exception as error:
        return {"source": "worldtides", "error": str(error)}


async def _copernicus_with_timeout(
    fetcher: Any, state: dict[str, Any], field: str
) -> dict[str, Any]:
    try:
        return await asyncio.wait_for(asyncio.to_thread(fetcher, state), timeout=20)
    except Exception as error:
        return {"source": "copernicusmarine", field: None, "error": str(error)}


async def ocean_agent(
    state: dict[str, Any], client: httpx.AsyncClient
) -> dict[str, Any]:
    tides, copernicus_data, copernicus_waves = await asyncio.gather(
        _worldtides_30_day(state, client),
        _copernicus_with_timeout(_fetch_copernicus_ocean_data, state, "sst_celsius"),
        _copernicus_with_timeout(
            _fetch_copernicus_wave_data, state, "significant_wave_height_m"
        ),
    )
    conditions = await _safe_get(
        client,
        "conditions",
        "/conditions",
        {"lat": state["lat"], "lon": state["lon"], "date": state["date"]},
    )
    return {
        "agent": "ocean_agent",
        "data": {
            "tides_30_day": tides,
            "copernicus": {**copernicus_data, "waves": copernicus_waves},
            **conditions,
        },
    }


async def pfz_agent(
    state: dict[str, Any], client: httpx.AsyncClient
) -> dict[str, Any]:
    params = {"lat": state["lat"], "lon": state["lon"]}
    favourable_params = {**params, "date": state["date"]}
    nearest, favourable = await asyncio.gather(
        _safe_get(client, "nearest_pfz", "/pfz/nearest", params),
        _safe_get(client, "favourable_zones", "/zones/favourable", favourable_params),
    )
    return {"agent": "pfz_agent", "data": {**nearest, **favourable}}


async def geospatial_agent(
    state: dict[str, Any], client: httpx.AsyncClient
) -> dict[str, Any]:
    hazards = await _safe_get(
        client,
        "hazards",
        "/hazards/nearby",
        {"lat": state["lat"], "lon": state["lon"]},
    )
    return {"agent": "geospatial_agent", "data": hazards}


async def _run_specialists(state: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        results = await asyncio.gather(
            marine_data_agent(state, client),
            weather_agent(state, client),
            ocean_agent(state, client),
            pfz_agent(state, client),
            geospatial_agent(state, client),
        )
    return {result["agent"]: result["data"] for result in results}


def _all_evidence(state: dict[str, Any]) -> dict[str, Any]:
    return state.get("specialist_results", {})


def risk_analysis_agent(state: dict[str, Any]) -> dict[str, Any]:
    evidence = _all_evidence(state)
    weather = evidence.get("weather_agent", {})
    geospatial = evidence.get("geospatial_agent", {})
    ocean = evidence.get("ocean_agent", {})
    alerts = weather.get("alerts", []) if isinstance(weather, dict) else []
    hazards = geospatial.get("hazards", {}) if isinstance(geospatial, dict) else {}
    boundary = hazards.get("imbl_boundary", {}) if isinstance(hazards, dict) else {}
    distance = boundary.get("distance_km") if isinstance(boundary, dict) else None
    active_alerts = bool(alerts) and not isinstance(alerts, dict) or bool(
        isinstance(alerts, dict) and (alerts.get("alerts") or alerts.get("active_alerts"))
    )
    try:
        near_imbl = distance is not None and float(distance) < 10
    except (TypeError, ValueError):
        near_imbl = False

    def contains_high_waves(value: Any) -> bool:
        if isinstance(value, dict):
            for key, nested_value in value.items():
                if key in {"significant_wave_height_m", "wave_height_m", "VHM0"}:
                    try:
                        if float(nested_value) > 3.0:
                            return True
                    except (TypeError, ValueError):
                        pass
                if contains_high_waves(nested_value):
                    return True
        elif isinstance(value, (list, tuple)):
            return any(contains_high_waves(item) for item in value)
        return False

    high_waves = contains_high_waves(ocean)
    warnings: list[str] = []
    if active_alerts:
        warnings.append("Active weather or cyclone alerts are present.")
    if near_imbl:
        warnings.append("The vessel is within 10 km of the IMBL boundary.")
    if high_waves:
        warnings.append("Significant wave height exceeds 3.0 meters.")
    risk_override = bool(warnings)
    return {
        **state,
        "risk": {"override": risk_override, "warnings": warnings},
        "risk_override": risk_override,
    }


def route_optimization_agent(state: dict[str, Any]) -> dict[str, Any]:
    risk = state.get("risk", {})
    return {
        **state,
        "route": {
            "status": "restricted" if risk.get("override") else "recommended",
            "waypoints": [{"lat": state["lat"], "lon": state["lon"]}],
            "reason": "; ".join(risk.get("warnings", [])) or "No immediate route hazards reported.",
        },
    }


def visualization_agent(state: dict[str, Any]) -> dict[str, Any]:
    evidence = _all_evidence(state)
    route = state.get("route", {})
    coordinates = [
        [waypoint["lon"], waypoint["lat"]]
        for waypoint in route.get("waypoints", [])
    ]
    features = [
        {
            "type": "Feature",
            "properties": {"status": route.get("status", "unknown")},
            "geometry": {
                "type": "LineString" if len(coordinates) > 1 else "Point",
                "coordinates": coordinates if len(coordinates) > 1 else (coordinates[0] if coordinates else [state["lon"], state["lat"]]),
            },
        }
    ]

    pfz_data = evidence.get("pfz_agent", {})
    pfz_points = []
    for key in ("nearest_pfz", "favourable_zones"):
        value = pfz_data.get(key) if isinstance(pfz_data, dict) else None
        pfz_points.extend(value if isinstance(value, list) else [value] if isinstance(value, dict) else [])
    for point in pfz_points:
        if not isinstance(point, dict) or point.get("lat") is None or point.get("lon") is None:
            continue
        features.append({
            "type": "Feature",
            "properties": {"type": "pfz", **{key: value for key, value in point.items() if key not in {"lat", "lon"}}},
            "geometry": {"type": "Point", "coordinates": [point["lon"], point["lat"]]},
        })

    weather_data = evidence.get("weather_agent", {})
    alerts = weather_data.get("alerts", []) if isinstance(weather_data, dict) else []
    for alert in alerts if isinstance(alerts, list) else []:
        if not isinstance(alert, dict):
            continue
        alert_lat = alert.get("lat", alert.get("latitude"))
        alert_lon = alert.get("lon", alert.get("longitude"))
        if alert_lat is None or alert_lon is None:
            continue
        features.append({
            "type": "Feature",
            "properties": {"type": "weather_alert", **{key: value for key, value in alert.items() if key not in {"lat", "lon", "latitude", "longitude"}}},
            "geometry": {"type": "Point", "coordinates": [alert_lon, alert_lat]},
        })

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }
    return {**state, "geojson": geojson}


def alert_notification_agent(state: dict[str, Any]) -> dict[str, Any]:
    risk = state.get("risk", {})
    return {
        **state,
        "notifications": [
            {"severity": "high", "message": warning}
            for warning in risk.get("warnings", [])
        ],
    }


def format_output(state: dict[str, Any]) -> dict[str, Any]:
    warnings = state.get("risk", {}).get("warnings", [])
    return {
        "query": state["query"],
        "final_answer": (
            "⚠ SAFETY WARNING: " + " ".join(warnings) + "\n\n"
            if warnings
            else ""
        )
        + "ORCA analysis completed.",
        "risk_override": bool(warnings),
        "specialist_results": state.get("specialist_results", {}),
        "route": state.get("route", {}),
        "geojson": state.get("geojson", {}),
        "notifications": state.get("notifications", []),
    }


async def run_orca_pipeline(
    query_text: str,
    lat: float,
    lon: float,
    date: str | None = None,
) -> dict[str, Any]:
    """Run ORCA orchestration, parallel specialists, and sequential safety stages."""
    state: dict[str, Any] = {
        "query": query_text,
        "lat": lat,
        "lon": lon,
        "date": _date_for_state(date),
    }
    state = await orchestrator(state)
    state = risk_analysis_agent(state)
    state = route_optimization_agent(state)
    state = visualization_agent(state)
    state = alert_notification_agent(state)
    return format_output(state)


__all__ = [
    "alert_notification_agent",
    "call_llm",
    "format_output",
    "geospatial_agent",
    "marine_data_agent",
    "ocean_agent",
    "orchestrator",
    "pfz_agent",
    "risk_analysis_agent",
    "route_optimization_agent",
    "run_orca_pipeline",
    "visualization_agent",
    "weather_agent",
]
