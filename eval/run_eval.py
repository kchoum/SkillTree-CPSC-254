"""
eval/run_eval.py
================
Measures two things:

  1. VALIDATION ACCURACY
     Tests the /api/validate-subject endpoint against labeled cases.
     Reports: accuracy %, false-positive rate, false-negative rate.

  2. FEEDBACK QUALITY
     Submits real code files to /api/code-feedback and scores each response
     on a rubric covering completeness, issue detection, actionability,
     score calibration, and tone.
     Reports: per-dimension scores and an overall feedback quality score.

Usage:
    # Make sure app.py is running first:  python app.py
    python eval/run_eval.py

    # Run only one suite:
    python eval/run_eval.py --suite validation
    python eval/run_eval.py --suite feedback

    # Point at a different host (e.g. a variant on port 5001):
    python eval/run_eval.py --base-url http://localhost:5001
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "http://localhost:5000"
CASES_FILE       = Path(__file__).parent / "eval_cases.json"
SAMPLES_DIR      = Path(__file__).parent / "samples"

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def post_json(base_url: str, path: str, payload: dict, timeout: int = 60) -> dict:
    url  = base_url.rstrip("/") + path
    body = json.dumps(payload).encode()
    req  = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())
    except Exception as exc:
        return {"error": str(exc)}


def post_multipart(base_url: str, path: str, file_path: Path,
                   fields: dict, timeout: int = 60) -> dict:
    """Send a multipart/form-data POST with one file and extra fields."""
    import io, uuid
    boundary = uuid.uuid4().hex
    body = io.BytesIO()

    def write(s: str):
        body.write(s.encode())

    # File field
    write(f"--{boundary}\r\n")
    write(f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n')
    write("Content-Type: text/plain\r\n\r\n")
    body.write(file_path.read_bytes())
    write("\r\n")

    # Extra text fields
    for name, value in fields.items():
        write(f"--{boundary}\r\n")
        write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n')
        write(str(value))
        write("\r\n")

    write(f"--{boundary}--\r\n")

    url = base_url.rstrip("/") + path
    req = urllib.request.Request(
        url,
        data=body.getvalue(),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())
    except Exception as exc:
        return {"error": str(exc)}

# ---------------------------------------------------------------------------
# Suite 1 — Validation accuracy
# ---------------------------------------------------------------------------

def run_validation_suite(base_url: str, cases: list) -> dict:
    print("\n" + "=" * 60)
    print("SUITE 1 — VALIDATION ACCURACY")
    print("=" * 60)

    results = []
    for case in cases:
        inp      = case["input"]
        expected = case["expected_valid"]
        note     = case.get("note", "")

        resp = post_json(base_url, "/api/validate-subject", {"subject": inp})
        got  = resp.get("valid", None)

        correct = (got == expected)
        status  = "✓" if correct else "✗"
        label   = "VALID" if expected else "INVALID"
        got_lbl = "valid" if got else ("invalid" if got is False else "ERROR")

        print(f"  {status}  [{label:7s}] '{inp}'")
        if not correct:
            print(f"       expected={expected}, got={got_lbl}  | {note}")
            if "message" in resp:
                print(f"       msg: {resp['message']}")

        results.append({
            "input":    inp,
            "expected": expected,
            "got":      got,
            "correct":  correct,
            "note":     note,
        })
        time.sleep(0.3)

    total    = len(results)
    correct  = sum(1 for r in results if r["correct"])
    accuracy = correct / total * 100

    fp = sum(1 for r in results if not r["expected"] and r["got"] is True)
    fn = sum(1 for r in results if r["expected"] and r["got"] is False)

    invalid_total = sum(1 for r in results if not r["expected"])
    valid_total   = sum(1 for r in results if r["expected"])

    fpr = fp / invalid_total * 100 if invalid_total else 0
    fnr = fn / valid_total   * 100 if valid_total   else 0

    print()
    print(f"  Accuracy           : {accuracy:.1f}%  ({correct}/{total})")
    print(f"  False-positive rate: {fpr:.1f}%  (non-CS accepted as CS)")
    print(f"  False-negative rate: {fnr:.1f}%  (CS rejected as non-CS)")

    return {
        "accuracy": accuracy,
        "fpr":      fpr,
        "fnr":      fnr,
        "total":    total,
        "correct":  correct,
        "details":  results,
    }

# ---------------------------------------------------------------------------
# Suite 2 — Feedback quality (strict rubric)
# ---------------------------------------------------------------------------

# Each dimension: (description, max_score)
FEEDBACK_RUBRIC = {
    # ── Structure ──────────────────────────────────────────────────────────
    "all_fields": (
        "All 6 required fields present: overall, strengths, improvements, "
        "style_notes, next_steps, score",
        2
    ),

    # ── Overall assessment ─────────────────────────────────────────────────
    "overall_length": (
        "overall is substantive: ≥2 sentences AND ≥100 characters",
        2
    ),
    "overall_specific": (
        "overall mentions at least one concrete element from the code "
        "(e.g. a method name, class name, or specific construct)",
        2
    ),

    # ── Issue detection ────────────────────────────────────────────────────
    "critical_issues_in_improvements": (
        "Every must_be_improvement issue appears as an actual improvements[] item "
        "(not just mentioned in overall or style_notes)",
        4
    ),
    "issue_keyword_coverage": (
        "Each expected issue has ≥1 required keyword present in its improvements[] entry",
        3
    ),

    # ── No false praise ────────────────────────────────────────────────────
    "no_forbidden_praise": (
        "None of the forbidden_praise phrases appear anywhere in the response",
        2
    ),

    # ── Improvement quality ────────────────────────────────────────────────
    "improvement_count": (
        "Number of improvements[] items ≥ min_improvements from case",
        2
    ),
    "code_example_quality": (
        "At least min_code_examples improvements have a code example "
        "with length ≥ min_example_length characters",
        3
    ),
    "suggestions_specific": (
        "Each improvement suggestion is ≥ 30 characters (not a one-liner platitude)",
        2
    ),

    # ── Score calibration ──────────────────────────────────────────────────
    "score_in_bounds": (
        "All three scores (correctness, readability, efficiency) fall within "
        "the case's score_bounds ranges",
        3
    ),
    "scores_differentiated": (
        "Not all three scores are identical (model is actually differentiating dimensions)",
        1
    ),

    # ── Proficiency appropriateness ────────────────────────────────────────
    "technical_language": (
        "Advanced/Intermediate responses use domain-specific terms; "
        "Beginner responses avoid unexplained jargon",
        2
    ),

    # ── Next steps ─────────────────────────────────────────────────────────
    "next_steps_count": (
        "At least 2 next_steps provided and each is ≥ 20 characters",
        1
    ),
}

ADVANCED_JARGON_REQUIRED = {
    "time complexity", "space complexity", "big o", "o(n", "o(log",
    "recursive", "iterative", "edge case", "invariant", "traversal",
    "algorithm", "data structure"
}
BEGINNER_FORBIDDEN_JARGON = {
    "amortized", "asymptotic", "invariant", "complexity class",
    "tail recursion", "memoization"
}


def score_feedback(fb: dict, case: dict) -> tuple[dict, list]:
    """Returns (scores_dict, list_of_failure_notes)."""
    scores = {}
    notes  = []
    proficiency     = case.get("proficiency", "Beginner")
    expected_issues = case.get("expected_issues", [])
    forbidden_praise= [p.lower() for p in case.get("forbidden_praise", [])]
    score_bounds    = case.get("score_bounds", {})
    min_improvements= case.get("min_improvements", 2)
    min_examples    = case.get("min_code_examples", 1)
    min_ex_len      = case.get("min_example_length", 20)

    improvements = fb.get("improvements", [])
    full_text    = json.dumps(fb).lower()

    # ── all_fields ──────────────────────────────────────────────────────────
    required = {"overall", "strengths", "improvements", "style_notes", "next_steps", "score"}
    missing  = required - fb.keys()
    if not missing:
        scores["all_fields"] = 2
    else:
        scores["all_fields"] = max(0, 2 - len(missing))
        notes.append(f"Missing fields: {missing}")

    # ── overall_length ──────────────────────────────────────────────────────
    overall = fb.get("overall", "")
    sentences = [s.strip() for s in overall.replace("!", ".").replace("?", ".").split(".") if len(s.strip()) > 10]
    if len(overall) >= 100 and len(sentences) >= 2:
        scores["overall_length"] = 2
    elif len(overall) >= 50:
        scores["overall_length"] = 1
        notes.append(f"overall too short or only 1 sentence ({len(overall)} chars, {len(sentences)} sentences)")
    else:
        scores["overall_length"] = 0
        notes.append(f"overall very short ({len(overall)} chars)")

    # ── overall_specific ───────────────────────────────────────────────────
    # Check if any method/class name from the code file appears in overall
    file_path = Path(__file__).parent.parent / case["file"]
    code_text = file_path.read_text(errors="replace").lower() if file_path.exists() else ""
    # Extract identifiers: words that appear in code and are ≥4 chars
    import re
    code_identifiers = set(re.findall(r'\b[a-z_][a-z_0-9]{3,}\b', code_text)) - {
        "self", "none", "true", "false", "return", "while", "class", "import", "from",
        "print", "append", "elif", "else", "pass", "with", "open", "read", "write"
    }
    overall_lower = overall.lower()
    found_ids = [i for i in code_identifiers if i in overall_lower]
    if found_ids:
        scores["overall_specific"] = 2
    else:
        scores["overall_specific"] = 0
        notes.append(f"overall doesn't reference any code identifiers (checked {len(code_identifiers)} candidates)")

    # ── critical_issues_in_improvements ────────────────────────────────────
    must_be = [ei for ei in expected_issues if ei.get("must_be_improvement")]
    imp_text_list = [
        (imp.get("issue", "") + " " + imp.get("suggestion", "")).lower()
        for imp in improvements
    ]
    imp_combined = " ".join(imp_text_list)

    detected_critical = 0
    for ei in must_be:
        keywords = [k.lower() for k in ei["required_keywords"]]
        # Must appear in the improvements array specifically, not just anywhere
        found_in_imp = any(
            any(kw in imp_text for kw in keywords)
            for imp_text in imp_text_list
        )
        if found_in_imp:
            detected_critical += 1
        else:
            notes.append(f"Critical issue '{ei['id']}' not found in improvements[] "
                         f"(keywords: {keywords})")

    if must_be:
        ratio = detected_critical / len(must_be)
        scores["critical_issues_in_improvements"] = round(ratio * 4)
    else:
        scores["critical_issues_in_improvements"] = 4

    # ── issue_keyword_coverage ─────────────────────────────────────────────
    covered = 0
    for ei in expected_issues:
        keywords = [k.lower() for k in ei["required_keywords"]]
        if any(kw in imp_combined for kw in keywords):
            covered += 1
        else:
            notes.append(f"Issue '{ei['id']}' keywords not found in improvements: {keywords}")

    if expected_issues:
        ratio = covered / len(expected_issues)
        scores["issue_keyword_coverage"] = round(ratio * 3)
    else:
        scores["issue_keyword_coverage"] = 3

    # ── no_forbidden_praise ────────────────────────────────────────────────
    found_praise = [p for p in forbidden_praise if p in full_text]
    if found_praise:
        scores["no_forbidden_praise"] = 0
        notes.append(f"Forbidden praise found: {found_praise}")
    else:
        scores["no_forbidden_praise"] = 2

    # ── improvement_count ──────────────────────────────────────────────────
    if len(improvements) >= min_improvements:
        scores["improvement_count"] = 2
    elif len(improvements) >= 1:
        scores["improvement_count"] = 1
        notes.append(f"Only {len(improvements)} improvement(s), expected ≥{min_improvements}")
    else:
        scores["improvement_count"] = 0
        notes.append("No improvements provided")

    # ── code_example_quality ───────────────────────────────────────────────
    good_examples = sum(
        1 for imp in improvements
        if len(imp.get("example", "").strip()) >= min_ex_len
    )
    if good_examples >= min_examples:
        scores["code_example_quality"] = 3
    elif good_examples > 0:
        scores["code_example_quality"] = 1
        notes.append(f"Only {good_examples} code example(s) with ≥{min_ex_len} chars, expected ≥{min_examples}")
    else:
        scores["code_example_quality"] = 0
        notes.append(f"No code examples with ≥{min_ex_len} chars")

    # ── suggestions_specific ───────────────────────────────────────────────
    short_suggestions = [
        imp.get("suggestion", "") for imp in improvements
        if len(imp.get("suggestion", "").strip()) < 30
    ]
    if not short_suggestions:
        scores["suggestions_specific"] = 2
    elif len(short_suggestions) <= 1:
        scores["suggestions_specific"] = 1
        notes.append(f"{len(short_suggestions)} suggestion(s) under 30 chars")
    else:
        scores["suggestions_specific"] = 0
        notes.append(f"{len(short_suggestions)} suggestions are too short/generic")

    # ── score_in_bounds ────────────────────────────────────────────────────
    sc = fb.get("score", {})
    out_of_bounds = []
    for dim, bounds in score_bounds.items():
        val = sc.get(dim)
        if not isinstance(val, int):
            out_of_bounds.append(f"{dim}=non-int({val})")
        elif not (bounds["min"] <= val <= bounds["max"]):
            out_of_bounds.append(f"{dim}={val} (expected {bounds['min']}–{bounds['max']})")

    if not out_of_bounds:
        scores["score_in_bounds"] = 3
    elif len(out_of_bounds) == 1:
        scores["score_in_bounds"] = 2
        notes.append(f"Score out of bounds: {out_of_bounds}")
    elif len(out_of_bounds) == 2:
        scores["score_in_bounds"] = 1
        notes.append(f"Scores out of bounds: {out_of_bounds}")
    else:
        scores["score_in_bounds"] = 0
        notes.append(f"All scores out of bounds: {out_of_bounds}")

    # ── scores_differentiated ──────────────────────────────────────────────
    sc_vals = [sc.get("correctness"), sc.get("readability"), sc.get("efficiency")]
    if len(set(v for v in sc_vals if isinstance(v, int))) >= 2:
        scores["scores_differentiated"] = 1
    else:
        scores["scores_differentiated"] = 0
        notes.append(f"All scores identical: {sc_vals}")

    # ── technical_language ─────────────────────────────────────────────────
    requires_tech = case.get("requires_technical_language", False)
    if proficiency == "Beginner":
        bad_jargon = [j for j in BEGINNER_FORBIDDEN_JARGON if j in full_text]
        if bad_jargon:
            scores["technical_language"] = 0
            notes.append(f"Unexplained advanced jargon in beginner response: {bad_jargon}")
        else:
            scores["technical_language"] = 2
    elif requires_tech:
        found_tech = [t for t in ADVANCED_JARGON_REQUIRED if t in full_text]
        if len(found_tech) >= 3:
            scores["technical_language"] = 2
        elif len(found_tech) >= 1:
            scores["technical_language"] = 1
            notes.append(f"Only {len(found_tech)} technical term(s) found: {found_tech}")
        else:
            scores["technical_language"] = 0
            notes.append("No domain-specific technical language found for advanced/intermediate response")
    else:
        scores["technical_language"] = 2

    # ── next_steps_count ───────────────────────────────────────────────────
    next_steps = fb.get("next_steps", [])
    good_steps = [s for s in next_steps if len(s.strip()) >= 20]
    if len(good_steps) >= 2:
        scores["next_steps_count"] = 1
    else:
        scores["next_steps_count"] = 0
        notes.append(f"Only {len(good_steps)} next step(s) with ≥20 chars")

    return scores, notes


def print_rubric_scores(label: str, rubric: dict, scores: dict, notes: list) -> tuple[int, int]:
    max_total = sum(v[1] for v in rubric.values())
    got_total = sum(scores.get(k, 0) for k in rubric)
    pct       = got_total / max_total * 100 if max_total else 0
    print(f"\n  {label}  [{got_total}/{max_total}  {pct:.0f}%]")
    for key, (desc, max_score) in rubric.items():
        got = scores.get(key, 0)
        bar = "✓" if got == max_score else ("~" if got > 0 else "✗")
        print(f"    {bar} {desc:<70s} {got}/{max_score}")
    if notes:
        print(f"\n  Failure notes:")
        for n in notes:
            print(f"    ⚠  {n}")
    return got_total, max_total


def run_feedback_suite(base_url: str, cases: list) -> dict:
    print("\n" + "=" * 60)
    print("SUITE 2 — FEEDBACK QUALITY  (strict rubric)")
    print("=" * 60)

    all_results = []

    for case in cases:
        file_path    = Path(__file__).parent.parent / case["file"]
        proficiency  = case["proficiency"]
        proj_desc    = case.get("project_description", "")
        learner_note = case.get("learner_note", "")
        note         = case.get("note", "")

        print(f"\n  ── {file_path.name} ({proficiency}) ──")
        print(f"     {note}")

        if not file_path.exists():
            print(f"     ERROR: file not found at {file_path}")
            all_results.append({"file": case["file"], "error": "file not found"})
            continue

        print("     Submitting for feedback…", end=" ", flush=True)
        fb = post_multipart(
            base_url, "/api/code-feedback", file_path,
            fields={
                "proficiency":         proficiency,
                "context":             learner_note,
                "project_description": proj_desc,
            }
        )

        if "error" in fb:
            print(f"ERROR: {fb['error']}")
            all_results.append({"file": case["file"], "error": fb["error"]})
            continue
        print("done")

        scores, failure_notes = score_feedback(fb, case)
        got, mx = print_rubric_scores("Feedback response", FEEDBACK_RUBRIC, scores, failure_notes)
        pct = got / mx * 100 if mx else 0
        print(f"\n     Overall feedback score: {pct:.1f}%")

        all_results.append({
            "file":          case["file"],
            "proficiency":   proficiency,
            "scores":        scores,
            "pct":           pct,
            "failure_notes": failure_notes,
        })
        time.sleep(0.5)

    valid = [r for r in all_results if "error" not in r]
    avg   = sum(r["pct"] for r in valid) / len(valid) if valid else None

    if avg is not None:
        print(f"\n  Average feedback quality: {avg:.1f}%")

    return {"cases": all_results, "average": avg}

# ---------------------------------------------------------------------------
# Save results
# ---------------------------------------------------------------------------

def save_results(val_results: dict, fb_results: dict):
    out_path = Path(__file__).parent / "eval_results.json"
    payload  = {
        "timestamp":  time.strftime("%Y-%m-%dT%H:%M:%S"),
        "validation": val_results,
        "feedback":   fb_results,
    }
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"\n  Results saved to {out_path}")

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Skill Tree LLM evaluation script")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL,
                        help="Base URL of the running Flask app")
    parser.add_argument("--suite", choices=["validation", "feedback", "all"],
                        default="all", help="Which suite to run")
    args = parser.parse_args()

    cases = json.loads(CASES_FILE.read_text())

    val_results = {}
    fb_results  = {}

    if args.suite in ("validation", "all"):
        val_results = run_validation_suite(args.base_url, cases["validation_cases"])

    if args.suite in ("feedback", "all"):
        fb_results = run_feedback_suite(args.base_url, cases["feedback_cases"])

    save_results(val_results, fb_results)

    if val_results and val_results.get("accuracy", 100) < 80:
        print("\n  ⚠  Validation accuracy below 80% threshold.")
        sys.exit(1)


if __name__ == "__main__":
    main()
