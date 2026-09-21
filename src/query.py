"""
Query pipeline: given a natural-language question, retrieve the most
relevant chunks from the vector store and generate a grounded answer
with citations.

Supports three LLM providers for generation, chosen via LLM_PROVIDER in
.env: "mistral" (default, free rate-limited tier), "groq" (free tier), or
"anthropic" (pay-as-you-go).

Usage:
    python src/query.py "How do I handle a failed webhook retry?"
"""

import os
import sys
import time

import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "stripe_docs"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # must match the model used in ingest.py

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "mistral").lower()  # "anthropic", "mistral", or "groq"
CLAUDE_MODEL = "claude-sonnet-4-6"
MISTRAL_MODEL = "mistral-small-2603"
GROQ_MODEL = "openai/gpt-oss-120b"  # model availability is per Groq account; check Groq().models.list()

# Chroma's default distance is squared L2 (lower = more similar). With
# all-MiniLM-L6-v2's normalized embeddings that is 2 * (1 - cosine
# similarity), so it ranges from 0 to 4 and 1.2 is roughly cosine 0.4.
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

    elif LLM_PROVIDER == "groq":
        from groq import Groq

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY not set. Copy .env.example to .env and add your key."
            )
        _llm_client = Groq(api_key=api_key)

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r} (expected 'anthropic', 'mistral', or 'groq')")
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
3. Keep the conditions and scope the excerpts attach to a statement
   (for example, which event type, product, or mode a behavior applies
   to). Do not generalize a narrow statement into a general rule.
4. If the excerpts don't contain enough information to answer the
   question, say so explicitly instead of guessing.

Documentation excerpts:
{context}

Question: {question}

Answer:"""


def generate_answer(prompt: str, max_retries: int = 3) -> str:
    """Call the configured LLM provider with the assembled prompt.

    Retries with exponential backoff on rate-limit (429) errors — the
    free tier's 1 request/second cap means a burst of test queries can
    trip this even when spaced a couple seconds apart.
    """
    client = _get_llm_client()

    for attempt in range(max_retries):
        try:
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

            elif LLM_PROVIDER == "groq":
                response = client.chat.completions.create(
                    model=GROQ_MODEL,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content

            else:
                raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r}")

        except Exception as e:
            is_rate_limit = "429" in str(e) or "rate_limited" in str(e).lower()
            if is_rate_limit and attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)  # 2s, 4s, 8s
                print(f"  Rate limited, retrying in {wait}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
                continue
            raise


def answer(question: str) -> tuple[str, list[dict]]:
    """Return (answer text, retrieved chunks). Chunks are returned even when
    we decline to answer, so callers can inspect what retrieval found."""
    chunks = retrieve(question)
    if not chunks or chunks[0]["distance"] > MAX_DISTANCE_THRESHOLD:
        return "I don't have enough information in the docs to answer that confidently.", chunks
    prompt = build_prompt(question, chunks)
    return generate_answer(prompt), chunks


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python src/query.py "<question>"')
        sys.exit(1)
    question = " ".join(sys.argv[1:])
    text, chunks = answer(question)
    print(text)
    if chunks:
        print("\nRetrieved excerpts:")
        for i, c in enumerate(chunks, start=1):
            print(f"  [{i}] {c['source']}  (distance {c['distance']:.3f})")
