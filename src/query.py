"""
Query pipeline: given a natural-language question, retrieve the most
relevant chunks from the vector store and generate a grounded answer
with citations.

Supports two LLM providers for generation — Claude (pay-as-you-go from
account creation) or Mistral (has a rate-limited free "Experiment" tier
on La Plateforme, good enough for a portfolio project's usage volume).
Set LLM_PROVIDER in .env to "anthropic" or "mistral".

Usage:
    python src/query.py "How do I handle a failed webhook retry?"
"""

import os
import sys

import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "stripe_docs"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # must match the model used in ingest.py

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "mistral").lower()  # "anthropic" or "mistral"
CLAUDE_MODEL = "claude-sonnet-4-6"
MISTRAL_MODEL = "mistral-large-latest"

# Chroma returns cosine *distance* (lower = more similar) by default.
# This is a placeholder — after running a few real queries, look at the
# distances that come back for good vs. bad matches and set this based
# on real numbers, then note the chosen value + reasoning in the README.
MAX_DISTANCE_THRESHOLD = 1.2

_embedder = None
_collection = None
_llm_client = None


def _get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


def _get_collection():
    global _collection
    if _collection is None:
        chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = chroma_client.get_or_create_collection(COLLECTION_NAME)
    return _collection


def _get_llm_client():
    """Lazily construct the configured LLM provider's client."""
    global _llm_client
    if _llm_client is not None:
        return _llm_client

    if LLM_PROVIDER == "anthropic":
        from anthropic import Anthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key."
            )
        _llm_client = Anthropic(api_key=api_key)

    elif LLM_PROVIDER == "mistral":
        # NOTE: as of the mistralai 2.x SDK, the client class lives at
        # mistralai.client.sdk.Mistral rather than the top-level package
        # (verified against the installed package layout — the SDK has
        # reorganized since older tutorials showing `from mistralai import
        # Mistral`). If a future SDK version restores that shortcut, either
        # import will work.
        from mistralai.client.sdk import Mistral

        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            raise RuntimeError(
                "MISTRAL_API_KEY not set. Copy .env.example to .env and add your key."
            )
        _llm_client = Mistral(api_key=api_key)

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r} (expected 'anthropic' or 'mistral')")

    return _llm_client


def retrieve(question: str, k: int = 5) -> list[dict]:
    """Return top-k chunks with their source + similarity score."""
    embedder = _get_embedder()
    collection = _get_collection()

    query_embedding = embedder.encode([question]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=k)

    if not results["documents"] or not results["documents"][0]:
        return []

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        chunks.append({"text": doc, "source": meta["source"], "distance": dist})
    return chunks


def build_prompt(question: str, chunks: list[dict]) -> str:
    """Assemble the retrieved context + question into a prompt that
    instructs the model to cite sources and refuse if unsure."""
    context_blocks = []
    for i, chunk in enumerate(chunks, start=1):
        context_blocks.append(f"[{i}] Source: {chunk['source']}\n{chunk['text']}")
    context = "\n\n".join(context_blocks)

    return f"""You are answering questions about Stripe's API using only the
documentation excerpts provided below. Follow these rules strictly:

1. Only use information present in the excerpts. Do not use outside
   knowledge about Stripe or make assumptions.
2. Cite the excerpt number(s) you used, like [1] or [1][3], after each
   claim.
3. If the excerpts don't contain enough information to answer the
   question, say so explicitly instead of guessing.

Documentation excerpts:
{context}

Question: {question}

Answer:"""


def generate_answer(prompt: str) -> str:
    """Call the configured LLM provider with the assembled prompt."""
    client = _get_llm_client()

    if LLM_PROVIDER == "anthropic":
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text")

    elif LLM_PROVIDER == "mistral":
        response = client.chat.complete(
            model=MISTRAL_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r}")


def answer(question: str) -> str:
    chunks = retrieve(question)
    if not chunks or chunks[0]["distance"] > MAX_DISTANCE_THRESHOLD:
        return "I don't have enough information in the docs to answer that confidently."
    prompt = build_prompt(question, chunks)
    return generate_answer(prompt)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python src/query.py "<question>"')
        sys.exit(1)
    question = " ".join(sys.argv[1:])
    print(answer(question))
