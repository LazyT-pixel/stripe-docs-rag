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

**Result: 14/15, but which question fails has moved and that move is the
real finding here.**

First pass: 2/3 trap questions correctly declined; the third (refund
processing, Q13) didn't invent a procedure but volunteered an unrelated fact
(that a `charge.refunded` webhook event exists) instead of cleanly declining.
I tightened the prompt's decline rule to stop that — told it a passing
mention of a related term isn't the same as having an answer.

That fixed Q13 (it now gives a single clean "the excerpts don't contain
this" sentence, no tangent) but broke Q2, which had previously answered
correctly. Q2's question is what to do when a PaymentIntent is `processing`,
and the docs state the answer plainly in one line: "Wait for the initiated
payment to succeed or fail." After the stricter rule, the model started
declining this too — same retrieved chunks, same distances, different
(wrong) output. The rule meant to stop the model from padding a decline with
irrelevant tangents had made it generally more trigger-happy to decline.

I then split the rule in two: one half says a short, caveated excerpt that
*directly names* the status/event in the question counts as enough to
answer (fixing Q2 without reopening Q13), the other half keeps the narrower
"a different, unrelated mention doesn't count as an answer" instruction
(keeping Q13 fixed). Re-running: Q13 stayed clean, but **Q2 regressed
again** — same wrong decline, same wording almost verbatim. Net result:
14/15, with Q2 now the failure instead of Q13.

This is unresolved as of now. I haven't confirmed whether the actual
retrieved chunks for Q2 include the sentence that answers it — the eval
report only shows source filenames and distances, not chunk text, so I
can't yet tell whether this is a prompt problem (the answer is right there
and the model still won't use it) or a retrieval problem (the answer never
makes the top-5 chunks, and the model is correctly saying it doesn't have
it). Next step is adding that visibility before touching the prompt again,
rather than continuing to guess at wording.

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

The decline-rule back-and-forth above (Q13 vs. Q2) was not a parameter
change — it's `build_prompt`'s rules 4-5 in `src/query.py`, if picking this
back up.

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
- **Tightening a decline rule to fix one question's over-sharing made a
  different question under-answer.** See Evaluation's Q13/Q2 writeup. Same
  retrieved chunks, same distances, different prompt wording, different
  (and in Q2's case, wrong) output. Prompt rules aren't independent knobs —
  a change aimed at one failure mode can shift the model's behavior on
  questions it previously got right. Still unresolved; next step is seeing
  the actual retrieved chunk text for Q2, not just source names and
  distances, before changing the wording again.
