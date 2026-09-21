"""
Ingestion pipeline: scrape a scoped subset of Stripe's docs, clean + chunk
the text, embed the chunks, and index them in a local Chroma vector store.

Scope (keep this tight — see README roadmap):
  - Payments
  - Webhooks
  - Subscriptions
  - Error handling

Usage:
    python src/ingest.py
"""

import sys
import time

import chromadb
import requests
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Pages to scrape. Keep this list short and deliberate rather than
# crawling the whole site — a scoped, well-understood corpus beats a huge
# noisy one for a 2-week project. Add more pages within these four
# sections as needed, but resist the urge to crawl the whole site.
SEED_URLS = [
    "https://docs.stripe.com/payments/payment-intents/verifying-status",
    "https://docs.stripe.com/webhooks/handling-payment-events",
    "https://docs.stripe.com/billing/subscriptions/overview",
    "https://docs.stripe.com/billing/subscriptions/webhooks",
    "https://docs.stripe.com/error-handling",
]

CHROMA_DIR = "./chroma_db"
COLLECTION_NAME = "stripe_docs"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # small, fast, good enough to start

INLINE_TAGS = ["a", "code", "span", "strong", "em", "b", "i", "kbd"]

# UI text that appears at the top of every Stripe docs page.
BOILERPLATE_LINES = {
    "Ask about this page",
    "Copy for LLM",
    "View as Markdown",
    "Install tools",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (portfolio-project RAG ingestion bot; "
        "personal/educational use)"
    )
}


def fetch_page(url: str, max_retries: int = 4) -> str:
    """Fetch raw HTML for a single doc page, retrying transient network
    errors (dropped TLS connections, timeouts, 5xx) with backoff."""
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            permanent = status is not None and 400 <= status < 500 and status != 429
            if permanent or attempt == max_retries - 1:
                raise
            wait = 2 ** (attempt + 1)  # 2s, 4s, 8s
            print(f"  Fetch failed ({type(e).__name__}), retrying in {wait}s... "
                  f"(attempt {attempt + 1}/{max_retries})")
            time.sleep(wait)


def clean_html(html: str) -> str:
    """Strip nav/sidebar/footer boilerplate, keep main article content."""
    soup = BeautifulSoup(html, "lxml")

    # Remove elements that are almost never useful signal in docs sites.
    for tag in soup(["nav", "header", "footer", "script", "style", "aside", "button"]):
        tag.decompose()

    # Stripe's docs put the article body in a <main> or <article> tag.
    # Fall back to <body> if neither is found (site structure may change).
    main = soup.find("main") or soup.find("article") or soup.find("body")
    if main is None:
        return ""

    # Inline elements (links, inline code, emphasis) must not be split onto
    # their own lines, or identifiers like `invoice.payment_failed` end up
    # as "invoice / . / payment / _ / failed", which hurts embeddings and
    # makes the excerpts hard for the LLM to read.
    for tag in main.find_all(INLINE_TAGS):
        tag.unwrap()
    main.smooth()

    text = main.get_text(separator="\n", strip=True)

    # Drop empty lines and known page-chrome lines from the docs site.
    lines = [
        line for line in text.splitlines()
        if line.strip() and line.strip() not in BOILERPLATE_LINES
    ]
    return "\n".join(lines)


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Fixed-size chunking with overlap, measured in characters.

    Simple on purpose — swap for semantic/header-aware chunking later if
    eval results show it's the bottleneck (see README stretch goals).
    """
    if not text:
        return []

    chunks = []
    start = 0
    text_len = len(text)
    step = chunk_size - overlap

    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += step

    return chunks


def embed_and_index(
    chunks: list[str],
    source_url: str,
    collection,
    embedder: SentenceTransformer,
) -> None:
    """Embed chunks and upsert into the local Chroma collection."""
    if not chunks:
        return

    embeddings = embedder.encode(chunks, show_progress_bar=False).tolist()
    ids = [f"{source_url}::chunk-{i}" for i in range(len(chunks))]
    metadatas = [{"source": source_url, "chunk_index": i} for i in range(len(chunks))]

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )


def main():
    # Phase 1: fetch and chunk everything BEFORE touching the index, so a
    # failed download can never leave us with a half-empty database.
    pages: dict[str, list[str]] = {}
    failed: list[str] = []
    for url in tqdm(SEED_URLS, desc="Fetching docs"):
        try:
            pages[url] = chunk_text(clean_html(fetch_page(url)))
            print(f"  Fetched {len(pages[url])} chunks from {url}")
        except requests.RequestException as e:
            failed.append(url)
            print(f"  Failed to fetch {url}: {e}")
        time.sleep(1)  # be a polite scraper

    if failed:
        print(f"\n{len(failed)} page(s) failed to download; leaving the existing "
              f"index untouched. Re-run to try again:")
        for url in failed:
            print(f"  - {url}")
        sys.exit(1)

    # Phase 2: rebuild from scratch so chunks from an older cleaning or
    # chunking strategy don't linger next to the new ones.
    print(f"Loading embedding model: {EMBEDDING_MODEL} ...")
    embedder = SentenceTransformer(EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # collection didn't exist yet
    collection = client.get_or_create_collection(COLLECTION_NAME)

    total_chunks = 0
    for url, chunks in pages.items():
        embed_and_index(chunks, source_url=url, collection=collection, embedder=embedder)
        total_chunks += len(chunks)

    print(f"\nDone. {total_chunks} total chunks indexed in '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    main()
