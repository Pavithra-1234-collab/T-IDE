from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


CHROMA_PATH = Path(__file__).with_name("chroma_db")
COLLECTION_NAME = "marine_knowledge"

client = chromadb.PersistentClient(path=str(CHROMA_PATH))
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"description": "Unstructured marine safety rules and knowledge"},
)
model = SentenceTransformer("all-MiniLM-L6-v2")

SAMPLE_DOCUMENTS = [
    (
        "Fishing rules require vessels to carry valid registration and fishing permits, "
        "follow seasonal restrictions, respect catch limits, and release protected species."
    ),
    (
        "Marine Protected Areas (MPAs) may prohibit fishing, anchoring, or landing. "
        "Before entering an MPA, check the current boundary coordinates and restriction type."
    ),
    (
        "The IMBL safety boundary separates maritime zones. Vessels must remain within "
        "authorized operating areas and report hazards or boundary concerns to the maritime authority."
    ),
    (
        "During a cyclone warning, secure fishing gear, return to a safe harbor when advised, "
        "monitor official weather broadcasts, avoid restricted waters, and do not sail into the storm."
    ),
]


def _populate_collection() -> None:
    embeddings = model.encode(SAMPLE_DOCUMENTS, normalize_embeddings=True).tolist()
    collection.upsert(
        ids=[f"marine-knowledge-{index}" for index in range(len(SAMPLE_DOCUMENTS))],
        documents=SAMPLE_DOCUMENTS,
        embeddings=embeddings,
    )


_populate_collection()


def retrieve_context(query: str, n_results: int = 2) -> list[str]:
    """Return the most relevant marine-knowledge documents for a query."""
    if n_results < 1:
        return []

    query_embedding = model.encode([query], normalize_embeddings=True).tolist()[0]
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents"],
    )
    return results.get("documents", [[]])[0]


__all__ = ["collection", "retrieve_context"]
