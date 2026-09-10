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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (portfolio-project RAG ingestion bot; "
        "personal/educational use)"
    )
}


def fetch_page(url: str) -> str:
    """Fetch raw HTML for a single doc page."""
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def clean_html(html: str) -> str:
    """Strip nav/sidebar/footer boilerplate, keep main article content."""
    soup = BeautifulSoup(html, "lxml")

    # Remove elements that are almost never useful signal in docs sites.
    for tag in soup(["nav", "header", "footer", "script", "style", "aside"]):
        tag.decompose()

    # Stripe's docs put the article body in a <main> or <article> tag.
    # Fall back to <body> if neither is found (site structure may change).
    main = soup.find("main") or soup.find("article") or soup.find("body")
    if main is None:
        return ""

    text = main.get_text(separator="\n", strip=True)

    # Collapse repeated blank lines left over from stripped elements.
    lines = [line for line in text.splitlines() if line.strip()]
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
    print(f"Loading embedding model: {EMBEDDING_MODEL} ...")
    embedder = SentenceTransformer(EMBEDDING_MODEL)

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(COLLECTION_NAME)

    total_chunks = 0
    for url in tqdm(SEED_URLS, desc="Ingesting docs"):
        try:
            html = fetch_page(url)
            text = clean_html(html)
            chunks = chunk_text(text)
            embed_and_index(chunks, source_url=url, collection=collection, embedder=embedder)
            total_chunks += len(chunks)
            print(f"  Indexed {len(chunks)} chunks from {url}")
        except requests.RequestException as e:
            print(f"  Failed to fetch {url}: {e}")

        # Be a polite scraper — small delay between requests.
        time.sleep(1)

    print(f"\nDone. {total_chunks} total chunks indexed in '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    main()
