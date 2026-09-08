from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    lat: float
    lon: float
    date: str | None = None


class CatchReport(BaseModel):
    user_id: str
    lat: float
    lon: float
    date: str
    catch_outcome: str
    species: str | None = None
    free_text_note: str | None = None


__all__ = ["QueryRequest", "CatchReport"]
