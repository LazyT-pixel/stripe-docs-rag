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
| Generation      | Pluggable via `LLM_PROVIDER`: Mistral (default, free tier), Groq (free tier), or Claude API |
| Interface       | CLI first, Streamlit if time allows |

## Roadmap

- [x] Scrape + clean a scoped subset of Stripe docs (5 pages across Payments, Webhooks, Subscriptions, Errors)
- [x] Chunking pipeline (800 chars, 100 overlap)
- [x] Embedding + vector store indexing
- [x] Retrieval + generation pipeline with citations
- [ ] "I don't know" handling for low-confidence retrieval (a distance threshold exists but is an untuned placeholder)
- [ ] 15-question eval set + scoring script (`eval/questions.md` is a blank template; no scoring script yet)
- [ ] README write-up with results, failure modes, what I'd do next
- [ ] (Stretch) Chunking strategy comparison
- [ ] (Stretch) Re-ranking step
- [ ] (Stretch) Streaming responses

## Out of scope (for now)

Multi-document-type support, auth/multi-user, fine-tuning, production infra.

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows PowerShell: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env          # Windows: copy .env.example .env; then add your API key(s)
```

## Usage

```bash
python src/ingest.py       # scrape + chunk + index docs (rebuilds the index each run)
python src/query.py "How do I handle a failed webhook retry?"
```

The answer is followed by the retrieved excerpts and their distances, so you
can check that each claim is actually supported by what retrieval returned.

## Evaluation

`eval/questions.md` holds the (not yet filled in) test set. A scoring script
is planned; results and analysis will be written up here once complete.

## What I learned / what broke

- **Model availability is per account.** Groq's `llama-3.3-70b-versatile` is
  a listed production model but returned a 404 for my key; `Groq().models.list()`
  showed which models my account could actually call.
- **A failed download silently emptied the index.** One page hit an SSL
  drop during ingest, and because ingest rebuilds the index, the page with the
  webhook-retry section was simply missing; the query then answered "the
  excerpts don't cover this". Ingest now retries transient failures, downloads
  every page before touching the index, and aborts without changes if any page
  still fails.
- **Answers can drift past their sources.** On "How do I handle a failed
  webhook retry?" the model cited the right page but also added a rationale
  for signature verification that no excerpt states, cited an error-handling
  excerpt for event names that come from the webhooks page, and restated the
  docs' "we won't attempt to charge the customer" line as a general rule. That
  line sits in the docs' "Successful invoice finalization" section, split from
  its `invoice.created` context by a chunk boundary, but the docs also say
  "this behavior applies to all webhook endpoints", so I have not confirmed
  the model's phrasing is wrong, only that it is under-scoped. A prompt rule
  telling the model to keep conditions attached to claims did not stop this on
  a second run. This is from one question, not a measured result; the eval set
  is meant to quantify it.
- **Tag-per-line text extraction hurt chunk quality.** Inline code like
  `invoice.payment_failed` was being split across five lines. The cleaner now
  unwraps inline tags before extracting text.
