import os
from typing import Any

import anthropic
import requests

try:
    from .rag import retrieve_context
except ImportError:
    from rag import retrieve_context


BASE_URL = "http://localhost:8000"


def call_llm(prompt: str) -> str:
    """Send a prompt to Anthropic and return the generated text."""
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()


def planning_agent(state: dict[str, Any]) -> dict[str, Any]:
    query = state["query"]
    prompt = f"""
Identify the data categories required to answer this fisherman's marine safety query:
{query}

Choose only the relevant categories from: PFZ, weather/alerts, sea conditions,
hazards, favourable zones. Return a concise comma-separated list of categories.
"""
    tasks = call_llm(prompt)
    return {**state, "tasks": tasks}


def _tasks_text(tasks: Any) -> str:
    if isinstance(tasks, (list, tuple, set)):
        return " ".join(str(task) for task in tasks).lower()
    return str(tasks or "").lower()


def _get_json(path: str, params: dict[str, Any]) -> Any:
    response = requests.get(f"{BASE_URL}{path}", params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def retrieval_agent(state: dict[str, Any]) -> dict[str, Any]:
    lat = state.get("lat")
    lon = state.get("lon")
    date = state.get("date")
    params = {"lat": lat, "lon": lon}
    tasks = _tasks_text(state.get("tasks"))
    retrieved_data: dict[str, Any] = {}

    endpoint_requests = []
    if any(keyword in tasks for keyword in ("pfz", "fishing zone", "potential fishing")):
        endpoint_requests.append(("pfz", "/pfz/nearest", params))
    if any(keyword in tasks for keyword in ("weather", "alert", "cyclone")):
        endpoint_requests.append(("alerts", "/alerts/nearby", params))
    if any(keyword in tasks for keyword in ("condition", "wind", "wave", "sea")):
        endpoint_requests.append(("conditions", "/conditions", {**params, "date": date}))
    if any(keyword in tasks for keyword in ("hazard", "imbl", "mpa", "protected")):
        endpoint_requests.append(("hazards", "/hazards/nearby", params))

    for name, path, request_params in endpoint_requests:
        try:
            retrieved_data[name] = _get_json(path, request_params)
        except requests.RequestException as error:
            retrieved_data[name] = {"error": str(error)}

    try:
        retrieved_data["marine_knowledge"] = retrieve_context(state["query"])
    except Exception as error:
        retrieved_data["marine_knowledge"] = {"error": str(error)}

    return {**state, "retrieved_data": retrieved_data}


def reasoning_agent(state: dict[str, Any]) -> dict[str, Any]:
    prompt = f"""
Draft a structured, practical response for a fisherman.

User query:
{state['query']}

Retrieved data:
{state.get('retrieved_data', {})}

Clearly separate recommended actions, conditions, and safety concerns. Do not invent
measurements or alerts that are absent from the retrieved data.
"""
    draft_answer = call_llm(prompt)
    return {**state, "draft_answer": draft_answer}


def _contains_active_alerts(alerts: Any) -> bool:
    if isinstance(alerts, list):
        return bool(alerts)
    if isinstance(alerts, dict):
        return bool(alerts.get("alerts")) or bool(alerts.get("active_alerts"))
    return False


def _imbl_distance_km(hazards: Any) -> float | None:
    if not isinstance(hazards, dict):
        return None
    boundary = hazards.get("imbl_boundary")
    if not isinstance(boundary, dict):
        return None
    distance = boundary.get("distance_km")
    return float(distance) if distance is not None else None


def risk_agent(state: dict[str, Any]) -> dict[str, Any]:
    retrieved_data = state.get("retrieved_data", {})
    alerts_active = _contains_active_alerts(retrieved_data.get("alerts"))
    imbl_distance = _imbl_distance_km(retrieved_data.get("hazards"))
    near_imbl = imbl_distance is not None and imbl_distance < 10
    risk_override = alerts_active or near_imbl

    warning = ""
    if alerts_active:
        warning = "⚠ UNSAFE: Active marine alerts are present. Follow official instructions and avoid hazardous waters.\n\n"
    elif near_imbl:
        warning = "⚠ CAUTION: You are within 10 km of the IMBL safety boundary. Confirm authorization and maintain a safe distance.\n\n"

    final_answer = warning + state.get("draft_answer", "")
    return {**state, "final_answer": final_answer, "risk_override": risk_override}


__all__ = [
    "BASE_URL",
    "call_llm",
    "planning_agent",
    "retrieval_agent",
    "reasoning_agent",
    "risk_agent",
]
