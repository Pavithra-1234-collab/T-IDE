# ORCA Copilot Instructions

## Project Context

ORCA is a marine safety and fishing-assistance system. The repository contains a FastAPI backend, PostgreSQL/PostGIS data access, ChromaDB retrieval, Sentence Transformers embeddings, and LangGraph agent orchestration.

Use Python 3.11+ syntax and keep application code under `backend/` unless a task explicitly requires another location.

## Stage 5 Architecture

Follow this architecture for multi-agent features:

- An orchestrator coordinates the workflow.
- Five specialist agents run in parallel where their work is independent.
- A sequential pipeline then performs risk assessment, route planning, and visualization.
- Agent state is represented as ordinary Python `dict` objects with explicit, stable keys.
- Keep specialist agents focused and make their inputs and outputs easy to test independently.

## Async and Data Fetching

- Prefer async-first implementations for new orchestration and agent code.
- Use `asyncio.gather` for independent parallel specialist-agent calls.
- Use `httpx.AsyncClient` for parallel calls to the Person 4 FastAPI endpoints at `http://localhost:8000`.
- Reuse an async HTTP client within a workflow when practical and always set request timeouts.
- Preserve useful error information in returned state instead of silently discarding failed data sources.

## LLM Calls

- Use Claude Sonnet through `anthropic.Anthropic()` for LLM calls, unless the surrounding API is explicitly asynchronous and the compatible async Anthropic client is required.
- Read API credentials from environment variables; never hard-code or commit secrets.
- Keep prompts explicit about the available evidence and instruct agents not to invent missing measurements, alerts, or recommendations.

## External Integrations

- Use `httpx` for WorldTides API requests and retrieve 30-day tide predictions when tide data is required.
- Use the `copernicusmarine` Python SDK for Copernicus Marine Data integration.
- Keep external API keys and service URLs in `.env` or environment variables. Do not expose them in logs or responses.
- Normalize external responses into the project’s ordinary dictionary state format before passing them to other agents.

## Existing Backend Conventions

- FastAPI is the HTTP layer in `backend/main.py`.
- SQL queries use SQLAlchemy `text()` with the existing `engine` from `backend/db.py`.
- Request validation uses Pydantic models from `backend/models.py`.
- Marine knowledge retrieval uses `retrieve_context` from `backend/rag.py`.
- The current LangGraph workflow is compiled as `orca_agent` in `backend/graph.py`.
- Keep the existing API routes and response contracts stable unless the task explicitly changes them.

## Engineering Practices

- Make the smallest focused change that satisfies the task.
- Prefer existing project patterns over new abstractions.
- Add or update focused tests for new agent behavior, endpoint calls, state transitions, and risk overrides.
- Validate Python syntax and run the narrowest relevant test or smoke check after edits.
- Do not commit generated model caches, local ChromaDB data, virtual environments, `.env` files, API keys, or database credentials.
