"""
Eval runner: executes every question in eval/questions.md through the real
query pipeline and reports how it did.

Grading is split by category because only one of them can be graded
automatically with any confidence:

  - trap: graded automatically. answer() returns a fixed string when
    retrieval confidence is too low (see src/query.py's MAX_DISTANCE_THRESHOLD
    check), so "did it decline?" is a simple equality check, not a guess.
  - factual / synthesis: NOT auto-graded. Whether a free-text LLM answer
    actually matches an expected answer is a judgment call (string
    containment and keyword overlap both produce false passes and false
    fails on short excerpts), and pretending otherwise would hide exactly
    the kind of error this project cares about catching. Instead this
    script prints the question, expected answer, actual answer, and the
    retrieved sources/distances side by side, and you read each one and
    record a pass/fail yourself. That's slower than a green checkmark, but
    it's honest about what a 5-page, non-LLM-judged eval can actually prove.

Usage:
    python eval/run_eval.py
    python eval/run_eval.py --out eval/results.md
"""

import argparse
import re
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))

import query as q  # noqa: E402

QUESTIONS_PATH = Path(__file__).resolve().parent / "questions.md"

# The exact string answer() returns when retrieval confidence is too low
# (the distance-threshold shortcut in src/query.py). Imported by value, not
# re-typed, so this can't drift from src/query.py.
DECLINE_TEXT = (
    "I don't have enough information in the docs to answer that confidently."
)

# The pipeline can ALSO decline without ever hitting that shortcut: if
# retrieval returns chunks under the distance threshold but none of them
# actually answer the question, the LLM declines on its own, per the
# prompt's "say so explicitly" rule (src/query.py build_prompt, rule 4).
# That wording varies by model and isn't a fixed string, so this looks for
# the phrases a real decline tends to use. This is a heuristic, not a
# perfect detector -- a false negative here (missing a real decline) is
# more likely than a false positive (the model rarely uses this kind of
# phrasing when it IS answering), so a result graded FAIL here is worth a
# manual read, same as any factual/synthesis question.
DECLINE_PHRASES = (
    "don't have enough information",
    "do not have enough information",
    "don't contain information",
    "do not contain information",
    "doesn't contain information",
    "does not contain information",
    "don't contain any information",
    "do not contain any information",
    "can't answer that question",
    "cannot answer that question",
)


def looks_like_decline(text: str) -> bool:
    if text.strip() == DECLINE_TEXT:
        return True
    lowered = text.lower()
    return any(phrase in lowered for phrase in DECLINE_PHRASES)


def parse_questions(path: Path) -> list[dict]:
    """Parse the markdown table in eval/questions.md into row dicts."""
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 4 or cells[0] in ("#", "") or set(cells[0]) == {"-"}:
            continue
        if not re.fullmatch(r"\d+", cells[0]):
            continue  # header or separator row
        num, question, expected, category = cells
        if not question:
            continue  # unfilled template row
        rows.append(
            {
                "num": int(num),
                "question": question,
                "expected": expected,
                "category": category,
            }
        )
    return rows


def run(rows: list[dict]) -> list[dict]:
    results = []
    for row in rows:
        text, chunks = q.answer(row["question"])
        declined = looks_like_decline(text)
        is_trap = row["category"].startswith("trap")

        auto_verdict = None
        if is_trap:
            auto_verdict = (
                "PASS"
                if declined
                else "FAIL (answered instead of declining) -- or just a decline "
                     "phrased unusually; read the Actual text before trusting this"
            )

        results.append(
            {
                **row,
                "actual": text,
                "declined": declined,
                "auto_verdict": auto_verdict,
                "chunks": chunks,
            }
        )
    return results


def format_report(results: list[dict]) -> str:
    lines = ["# Eval results", ""]
    trap_total = sum(1 for r in results if r["category"].startswith("trap"))
    trap_pass = sum(1 for r in results if r["auto_verdict"] == "PASS")
    lines.append(
        f"Trap questions (auto-graded): {trap_pass}/{trap_total} correctly declined."
    )
    lines.append(
        f"Factual + synthesis questions: {sum(1 for r in results if not r['category'].startswith('trap'))} "
        "— read each one below and judge for yourself; no auto-grade."
    )
    lines.append("")

    for r in results:
        lines.append(f"## Q{r['num']} [{r['category']}]")
        lines.append(f"**Question:** {r['question']}")
        lines.append(f"**Expected:** {r['expected']}")
        lines.append(f"**Actual:** {r['actual']}")
        if r["auto_verdict"]:
            lines.append(f"**Auto-verdict:** {r['auto_verdict']}")
        else:
            lines.append("**Your verdict:** PASS / FAIL  _(fill in)_")
        if r["chunks"]:
            srcs = ", ".join(
                f"{c['source'].rsplit('/', 1)[-1]} ({c['distance']:.3f})"
                for c in r["chunks"][:3]
            )
            lines.append(f"**Top retrieved sources:** {srcs}")
        else:
            lines.append("**Top retrieved sources:** (none)")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=None, help="Write the report to this file instead of stdout.")
    args = parser.parse_args()

    rows = parse_questions(QUESTIONS_PATH)
    if not rows:
        print("No filled-in questions found in eval/questions.md.", file=sys.stderr)
        sys.exit(1)

    print(f"Running {len(rows)} questions through the pipeline...", file=sys.stderr)
    results = run(rows)
    report = format_report(results)

    if args.out:
        args.out.write_text(report, encoding="utf-8")
        print(f"Wrote report to {args.out}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
