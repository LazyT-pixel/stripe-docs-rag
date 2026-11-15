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
- [x] "I don't know" handling for low-confidence retrieval (threshold set from real eval distances, see Evaluation)
- [x] 15-question eval set + scoring script (`eval/questions.md` + `eval/run_eval.py`)
- [x] README write-up with results, failure modes, what I'd do next
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

`eval/questions.md` holds 15 questions: 8 factual, 4 requiring synthesis
across 2+ chunks, and 3 "trap" questions outside the scope of the 5 indexed
pages (refunds, Connect payouts, Stripe Tax rates), which should be declined
rather than answered.

```bash
python eval/run_eval.py --out eval/results.md
```

The script auto-grades only the trap questions, by checking whether the
answer matches the pipeline's fixed decline string OR uses decline-like
phrasing (`looks_like_decline()` in `eval/run_eval.py`) — the model can
legitimately decline either via the distance-threshold shortcut or on its
own judgment per the prompt's "say so explicitly" rule, and both count.
Factual and synthesis questions are not auto-graded; free-text answers were
read and judged by hand, because a string/keyword check produces both false
passes and false fails on short excerpts, which would hide the exact kind
of error this project cares about catching.

**Result: 14/15.** All 8 factual and all 4 synthesis questions passed
manual review. 2/3 trap questions correctly declined (Connect payouts, Stripe
Tax rates); the third (refund processing) failed — the model didn't invent a
refund procedure, but it also didn't cleanly decline. It volunteered that the
docs mention a `charge.refunded` webhook event (true, and retrieved) while
explaining it couldn't describe the refund steps themselves (also true). That
sits in between "hallucinated" and "declined", and I'm counting it as a fail
since the question asked for a procedure and the honest answer is "I don't
know", not a tour of a tangentially related webhook event.

Two parameters were changed based on this run's actual numbers, not guesses:
- `MAX_DISTANCE_THRESHOLD` (1.2 → 1.35): the legitimate questions' top
  retrieved distance ranged 0.389–1.278, and the trap questions' ranged
  0.674–1.396. Those ranges overlap — a trap question can score a lower
  (more "confident") distance than a real one — so no single threshold can
  cleanly separate them. 1.2 was below a real question's distance (Q12,
  1.278), causing it to be auto-declined before the model ever saw it.
  1.35 clears that case while still catching catastrophic retrieval misses.
  The actual filtering of out-of-scope questions is mostly done by the
  prompt's own "say so if the excerpts don't cover it" rule, not this
  threshold — the threshold is a backstop, not the real mechanism.
- `max_tokens` (1000 → 1800, all three providers): a synthesis answer
  that built a markdown table ran out of budget and was cut off mid-word.

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
- **A distance threshold alone can't separate in-scope from out-of-scope
  questions.** See Evaluation — trap and legitimate questions' distances
  overlap in this corpus. The prompt-level "decline if the excerpts don't
  cover it" instruction is doing the real work; the distance threshold only
  catches the worst retrieval misses.
- **My own eval script's grading was wrong, not just the pipeline.** The
  first run reported 0/3 trap questions passing. All three had actually
  declined correctly — just with different wording than the one fixed
  string I was checking for. Worth remembering when a "0% pass rate"
  shows up: check the grader before concluding the thing you're testing
  is broken.
