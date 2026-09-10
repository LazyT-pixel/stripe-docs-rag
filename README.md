# Stripe Docs Q&A (RAG)

> Status: 🚧 In progress — started August 2026

A retrieval-augmented Q&A tool over Stripe's public API documentation. Ask a
question in plain English (e.g. "How do I handle a failed webhook retry?")
and get an answer grounded in the actual docs, with citations back to the
source page.

## Why this project

Most "chat with your docs" demos run on Wikipedia or generic PDFs. Stripe's
docs are dense, code-heavy, and version-sensitive — a good stress test for
chunking strategy, retrieval quality, and knowing when the model should say
"I don't know" instead of guessing.

## Problem statement

Given a natural-language question about the Stripe API, retrieve the most
relevant documentation chunks and generate an answer that:
- Is grounded in retrieved content (not hallucinated)
- Cites the source page/section
- Explicitly declines to answer when retrieval confidence is low

## Stack

| Component      | Choice                          |
|-----------------|----------------------------------|
| Ingestion       | `requests` + `BeautifulSoup`     |
| Chunking        | Fixed-size w/ overlap (start simple) |
| Embeddings      | Local (sentence-transformers, `all-MiniLM-L6-v2`) |
| Vector store    | Chroma (local, zero setup)       |
| Generation      | Mistral API (free "Experiment" tier) — Claude API supported as a swap-in alternative |
| Interface       | CLI first, Streamlit if time allows |

## Roadmap

- [ ] Scrape + clean a scoped subset of Stripe docs (Payments, Webhooks, Subscriptions, Errors)
- [ ] Chunking pipeline
- [ ] Embedding + vector store indexing
- [ ] Retrieval + generation pipeline with citations
- [ ] "I don't know" handling for low-confidence retrieval
- [ ] 15-question eval set + scoring script
- [ ] README write-up with results, failure modes, what I'd do next
- [ ] (Stretch) Chunking strategy comparison
- [ ] (Stretch) Re-ranking step
- [ ] (Stretch) Streaming responses

## Out of scope (for now)

Multi-document-type support, auth/multi-user, fine-tuning, production infra.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your API key(s)
```

## Usage

```bash
python src/ingest.py       # scrape + chunk + index docs
python src/query.py "How do I handle a failed webhook retry?"
```

## Evaluation

See `eval/questions.md` for the test set and `eval/run_eval.py` for the
scoring script. Results and analysis will be written up here once complete.

## What I learned / what broke

_(to be filled in as the project progresses)_
