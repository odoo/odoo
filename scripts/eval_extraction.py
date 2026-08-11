#!/usr/bin/env python3
"""Repeatable extraction eval: prompt files, JSON run records, A/B modes.

Usage (repo root, inside the rebuilt odoo image — pydantic/anthropic live there):

    python scripts/eval_extraction.py --prompt prompts/v1.md
    python scripts/eval_extraction.py --prompt prompts/v1.md --input document
    python scripts/eval_extraction.py --prompt prompts/v2.md \\
        --out runs/v2-text.json --input text
    python scripts/eval_extraction.py --live   # deprecated alias: v1 + live

Every accuracy number maps back to the exact prompt bytes: the system prompt
is read from ``--prompt`` (never hard-coded here), the golden set is fixed,
and each run emits a JSON run record that logs timestamp, model, prompt
path, per-field precision, overall accuracy, usage and latency.

Offline mode (default, no API key) replays a frozen answer so CI stays
deterministic; ``--live`` calls the real Anthropic API.

Week-7 confidence milestone — the script now answers two extra questions:

1. **Is the self-reported certainty calibrated?** The model fills
   ``field_confidence`` (per field group + ``overall``). We compare that
   stated certainty against actual per-invoice correctness and report a
   point-biserial correlation. A strong positive correlation means the
   model's "I'm 95% sure" is actually worth something; a near-zero one means
   the stated floats are noise and the routing threshold must lean on the
   deterministic blend instead (the "calibrate, don't trust" lesson).

2. **What does the threshold curve look like?** For 0.7 / 0.8 / 0.9 we
   compute the auto-approval rate and the error rate among approved records
   — for both the *stated* confidence and the *calibrated*
   ``combined_confidence`` score (arithmetic check + VAT/IBAN rescue +
   self-report blend from ``models/confidence.py``). The table is what the
   week-7 review DB query (~0.7/0.8/0.9) is meant to replicate at
   production scale; ``--curve`` dumps the numbers as CSV.
"""

import argparse
import csv
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = (
    REPO_ROOT / "custom_addons" / "invoice_agent" / "tests" / "fixtures" / "golden_set.json"
)

# Make ``custom_addons`` importable as a namespace package when running from
# the repo root without the Odoo runtime on sys.path.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SCALAR_FIELDS = [
    "vendor_name",
    "vendor_vat",
    "invoice_date",
    "due_date",
    "currency",
    "subtotal",
    "tax_total",
    "amount_total",
]
LINE_FIELDS = ["name", "quantity", "price_unit"]
LINE_FIELDS_DISPLAY = "lines"

# Thresholds probed by the week-7 tuning query (the brief lists 0.7/0.8/0.9).
THRESHOLDS = (0.7, 0.8, 0.9)
# OCR mean confidence assumed by the offline eval when no Tesseract conf is
# available (the frozen answer path). Live/full-pipeline runs override with
# the real ocr_confidence.
OFFLINE_OCR_CONFIDENCE = 0.9
# Offline self-reported confidence for clean vs deliberately-awful scans.
# The awful set states a *low* certainty honestly; the calibration section
# then checks the stated number actually predicts correctness.
CLEAN_SELF_REPORT = 0.95
AWFUL_SELF_REPORT = 0.55


def load_golden_set():
    with open(GOLDEN_PATH, encoding="utf-8") as handle:
        return json.load(handle)["invoices"]


def load_prompt(prompt_path):
    """Return the byte-exact system prompt text from a prompts/*.md file."""
    path = Path(prompt_path)
    if not path.exists():
        path = REPO_ROOT / path
    if not path.exists():
        print(f"Error: prompt file not found: {prompt_path}", file=sys.stderr)
        sys.exit(2)
    return path.read_text(encoding="utf-8")


def value_equal(actual, expected, tolerance=0.01):
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return abs(float(actual) - float(expected)) <= tolerance
    return str(actual).strip().lower() == str(expected).strip().lower()


def compare_lines(actual_lines, expected_lines):
    """Lines are positional: a line scores 1 when name/quantity/price_unit all
    match (within tolerance) against the expected line at the same index."""
    total = max(len(actual_lines), len(expected_lines))
    if not total:
        return 1.0
    correct = 0
    for expected_line, actual_line in zip(expected_lines, actual_lines):
        if not actual_line or not expected_line:
            continue
        if all(
            value_equal(actual_line.get(field), expected_line.get(field))
            for field in LINE_FIELDS
        ):
            correct += 1
    return correct / total


def extraction_to_plain(extraction):
    if isinstance(extraction, dict):
        return extraction
    return extraction.model_dump()


def _row_correct(row):
    """A row is 'correct' when every scalar field matched AND the lines match."""
    if not all(row.get(field) for field in SCALAR_FIELDS):
        return False
    return row.get(LINE_FIELDS_DISPLAY, 0.0) >= 1.0


def _load_confidence_module():
    """Load models/confidence.py directly, outside the Odoo runtime.

    Mirrors ``_load_invoice_extraction_schema`` — we only need the pure
    functions (combined_confidence), and importing the odoo-bound package
    __init__ would require the full ORM environment.
    """
    import importlib.util

    module_path = (
        REPO_ROOT / "custom_addons" / "invoice_agent" / "models" / "confidence.py"
    )
    spec = importlib.util.spec_from_file_location(
        "invoice_agent_confidence",
        module_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_CONFIDENCE = _load_confidence_module()


def _calibrated_score(parsed, ocr_text=None, ocr_confidence=None):
    """Run the deterministic blend over an extracted payload dict.

    ``parsed`` is the plain dict from ``extraction_to_plain`` (Decimals and
    dates may still be present when coming straight from a pydantic dump —
    ``combined_confidence`` handles both). Returns 0..1.
    """
    score, _details = _CONFIDENCE.combined_confidence(
        parsed,
        ocr_text=ocr_text,
        ocr_confidence=ocr_confidence,
    )
    return score


def _pearson(xs, ys):
    """Pearson correlation; None when the sample has no variance."""
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if not den_x or not den_y:
        return None
    return num / (den_x * den_y)


def _threshold_curve(rows, score_key):
    """Auto-approval rate + error rate among approved, per threshold.

    :param rows: list of row dicts (each with ``_score`` and ``correct``).
    :param score_key: which score to read from each row
        (``stated_score`` or ``calibrated_score``).
    :return: list of dicts, one per threshold.
    """
    curve = []
    for threshold in THRESHOLDS:
        approved = [row for row in rows if row[score_key] >= threshold]
        approved_count = len(approved)
        auto_rate = approved_count / len(rows) if rows else 0.0
        errors = [row for row in approved if not row["correct"]]
        error_rate = len(errors) / approved_count if approved_count else 0.0
        curve.append(
            {
                "threshold": threshold,
                "auto_approval_rate": round(auto_rate, 4),
                "error_rate_among_approved": round(error_rate, 4),
                "false_auto_approvals": len(errors),
                "approved": approved_count,
            },
        )
    return curve


def run_eval(extractor, golden):
    """Run the extractor on every golden invoice; return per-field stats.

    Each row additionally carries the week-7 confidence signals:
    ``stated_score`` (the model's self-reported overall confidence, when
    present) and ``calibrated_score`` (the deterministic blend from
    ``models/confidence.py`` — arithmetic + VAT/IBAN rescue + self-report).
    The calibration table in :func:`print_report` compares the two.
    """
    per_field = {field: {"correct": 0, "total": 0} for field in SCALAR_FIELDS}
    per_field[LINE_FIELDS_DISPLAY] = {"correct": 0, "total": 0}
    rows = []
    latencies_ms = []

    for invoice in golden:
        started = time.perf_counter()
        parsed = extraction_to_plain(extractor(invoice))
        latencies_ms.append((time.perf_counter() - started) * 1000.0)

        expected = invoice["expected"]
        row = {"id": invoice["id"]}
        for field in SCALAR_FIELDS:
            per_field[field]["total"] += 1
            row[field] = value_equal(parsed.get(field), expected.get(field))
            if row[field]:
                per_field[field]["correct"] += 1

        line_accuracy = compare_lines(
            parsed.get("lines") or [], expected.get("lines") or [],
        )
        per_field[LINE_FIELDS_DISPLAY]["total"] += 1
        row[LINE_FIELDS_DISPLAY] = line_accuracy
        if line_accuracy >= 1.0:
            per_field[LINE_FIELDS_DISPLAY]["correct"] += 1
        rows.append(row)

        # Week-7 confidence signals -------------------------------
        reported = parsed.get("field_confidence") or {}
        if isinstance(reported, dict):
            stated = reported.get("overall")
        else:
            stated = None
        try:
            row["stated_score"] = float(stated) if stated is not None else None
        except (TypeError, ValueError):
            row["stated_score"] = None
        row["calibrated_score"] = _calibrated_score(
            parsed,
            ocr_text=invoice.get("text"),
            ocr_confidence=OFFLINE_OCR_CONFIDENCE,
        )
        row["correct"] = _row_correct(row)

    return per_field, rows, latencies_ms


def calibration_block(rows):
    """Correlation + threshold curves for stated vs calibrated confidence.

    Returns None when no row carries a stated score (the model omitted
    ``field_confidence`` entirely) — the report then skips the stated curve
    instead of printing a misleading zero-correlation line.
    """
    stated_rows = [row for row in rows if row.get("stated_score") is not None]
    if not stated_rows:
        return {
            "stated_correlation": None,
            "stated_curve": [],
            "calibrated_curve": _threshold_curve(rows, "calibrated_score"),
            "stated_coverage": 0.0,
        }

    correlation = _pearson(
        [row["stated_score"] for row in stated_rows],
        [1.0 if row["correct"] else 0.0 for row in stated_rows],
    )
    return {
        "stated_correlation": (
            round(correlation, 4) if correlation is not None else None
        ),
        "stated_curve": _threshold_curve(stated_rows, "stated_score"),
        "calibrated_curve": _threshold_curve(rows, "calibrated_score"),
        "stated_coverage": round(len(stated_rows) / len(rows), 4) if rows else 0.0,
    }


def summarize(per_field, rows, latencies_ms):
    """Build a plain dict run record (JSON-serializable, no Path objects)."""
    total_fields = sum(entry["total"] for entry in per_field.values())
    total_correct = sum(entry["correct"] for entry in per_field.values())
    overall = total_correct / total_fields if total_fields else 0.0

    field_accuracy = {}
    for field, entry in per_field.items():
        field_accuracy[field] = entry["correct"] / entry["total"] if entry["total"] else 0.0

    worst_field = min(field_accuracy, key=field_accuracy.get)
    best_field = max(field_accuracy, key=field_accuracy.get)

    return {
        "overall_accuracy": round(overall, 4),
        "fields": {field: round(acc, 4) for field, acc in field_accuracy.items()},
        "best_field": best_field,
        "worst_field": worst_field,
        "invoices_scored": len(rows),
        "latency_ms_avg": round(sum(latencies_ms) / len(latencies_ms), 2) if latencies_ms else None,
        "confidence": calibration_block(rows),
        "rows": rows,
    }


def _print_curve_table(title, curve):
    print(f"\n{title}")
    print(
        f"{'Threshold':>10} {'Auto-approval':>15} {'Error among ok':>16} "
        f"{'False auto':>12} {'Approved':>9}"
    )
    print("-" * 66)
    for entry in curve:
        print(
            f"{entry['threshold']:>10.2f} "
            f"{entry['auto_approval_rate'] * 100:>14.1f}% "
            f"{entry['error_rate_among_approved'] * 100:>15.1f}% "
            f"{entry['false_auto_approvals']:>12d} "
            f"{entry['approved']:>9d}"
        )


def print_report(per_field, rows, latencies_ms):
    total_fields = sum(entry["total"] for entry in per_field.values())
    total_correct = sum(entry["correct"] for entry in per_field.values())

    print("\n=== Extraction Accuracy ===\n")
    print(f"{'Field':<18}{'Accuracy':>10}")
    print("-" * 30)
    for field, entry in per_field.items():
        accuracy = entry["correct"] / entry["total"] if entry["total"] else 0.0
        print(f"{field:<18}{accuracy * 100:>9.1f}%")
    overall = total_correct / total_fields if total_fields else 0.0
    print("-" * 30)
    print(f"{'OVERALL':<18}{overall * 100:>9.1f}%")
    if latencies_ms:
        print(f"\nAvg latency: {sum(latencies_ms) / len(latencies_ms):.0f} ms "
              f"({len(latencies_ms)} invoices)")
    print(f"\nInvoices scored: {len(rows)}")

    for row in rows:
        misses = [
            field
            for field in (*SCALAR_FIELDS, LINE_FIELDS_DISPLAY)
            if (field == LINE_FIELDS_DISPLAY and row[field] < 1.0)
            or (field != LINE_FIELDS_DISPLAY and not row[field])
        ]
        if misses:
            print(f"  {row['id']}: missed {', '.join(misses)}")

    # ---- Week-7 calibration report -----------------------------------
    cal = calibration_block(rows)
    print("\n=== Confidence Calibration (week 7) ===\n")
    if cal["stated_correlation"] is not None:
        print(
            "Correlation between self-reported confidence and correctness: "
            f"{cal['stated_correlation']:.3f}"
        )
        print(
            "  >0.5: the model's stated certainty is informative — keep the "
            "self-report weight.\n"
            "  ~0: stated confidence is noise — routing must rely on the "
            "deterministic blend."
        )
    else:
        print("The model did not state any field_confidence — no stated curve.")
    print(f"Stated-confidence coverage: {cal['stated_coverage'] * 100:.0f}% of rows")

    _print_curve_table("Stated confidence — auto-approval vs error rate", cal["stated_curve"])
    _print_curve_table(
        "Calibrated blend — auto-approval vs error rate",
        cal["calibrated_curve"],
    )
    print(
        "\nThe brief commits the chosen threshold as a config parameter "
        "(invoice_agent.confidence_threshold). The calibrated row above is "
        "what the production SQL query (scripts/tune_threshold.sql) verifies "
        "at scale over invoice_agent_usage x account_move."
    )
    return overall


def _load_invoice_extraction_schema():
    """Load invoice_extraction.py directly, bypassing the odoo-dependent
    ``invoice_agent`` package __init__ (which imports every model)."""
    import importlib.util

    module_path = (
        REPO_ROOT / "custom_addons" / "invoice_agent" / "models" / "invoice_extraction.py"
    )
    spec = importlib.util.spec_from_file_location(
        "invoice_agent_invoice_extraction",
        module_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def offline_extractor(prompt_text=None):
    """Validate a frozen answer through the real schema; deterministic.

    The frozen answer is derived per-invoice from the golden set's own
    ground truth, keyed by invoice id:

    * clean scans (``id`` not starting with ``awful_``) — the extractor
      "reads" every field exactly as hand-labelled: every one of the 15
      clean invoices is extracted correctly, and the model states a high
      0.95 overall confidence.
    * deliberately awful scans (``id`` starting with ``awful_``) — the same
      per-invoice expected payload but ``amount_total`` is OCR-garbled to
      9999.00 (the arithmetic cross-check must catch it) and the model
      *honestly* states a low 0.55 overall certainty.

    That variance is what makes the calibration section measurable in CI:
    stated confidence says awful is worse, the arithmetic check agrees, and
    the 0.8 threshold table keeps the false auto-approvals at zero while the
    clean majority still rides the Auto column.
    """
    schema = _load_invoice_extraction_schema()
    InvoiceExtraction = schema.InvoiceExtraction

    def _clean_answer(invoice):
        """Ground-truth payload with a confident, calibrated self-report."""
        expected = invoice["expected"]
        answer = dict(expected)
        answer["lines"] = [dict(line) for line in expected.get("lines") or []]
        answer["field_confidence"] = {
            "overall": CLEAN_SELF_REPORT,
            "vendor_name": 0.98,
            "vendor_vat": 0.95 if expected.get("vendor_vat") else None,
            "invoice_date": 0.97,
            "due_date": 0.96,
            "currency": 1.0,
            "subtotal": 0.96,
            "tax_total": 0.96,
            "amount_total": 0.97,
            "lines": 0.95,
        }
        answer["notes"] = None
        return answer

    def _awful_answer(invoice):
        """Same payload, but the TOTAL is garbled and certainty is low."""
        answer = _clean_answer(invoice)
        # A torn totals section: both the subtotal and the TOTAL are
        # unreadable, so the arithmetic check has no sane target to compare
        # the (otherwise intact) line items against — that is exactly the
        # signal that must route the bill to Needs Review. The honest low
        # self-report corroborates.
        answer["subtotal"] = None
        answer["tax_total"] = None
        answer["amount_total"] = 9999.0
        answer["field_confidence"]["overall"] = AWFUL_SELF_REPORT
        answer["field_confidence"]["subtotal"] = 0.2
        answer["field_confidence"]["tax_total"] = 0.2
        answer["field_confidence"]["amount_total"] = 0.3
        answer["field_confidence"]["vendor_vat"] = 0.4
        answer["notes"] = (
            "OCR garbled the totals section — the line items do not match "
            "the printed 9999.00 TOTAL."
        )
        return answer

    def extract(invoice):
        if str(invoice["id"]).startswith("awful_"):
            answer = _awful_answer(invoice)
        else:
            answer = _clean_answer(invoice)
        return InvoiceExtraction.model_validate(answer)

    return extract


def live_extractor(prompt_text, input_mode):
    """Real structured extraction through ``client.messages.parse``.

    ``input_mode`` switches the user turn between OCR text and a native
    Claude document block (base64 PDF) — the A/B comparison the eval harness
    exists for. Requires ANTHROPIC_API_KEY.
    """
    import os

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: --live requires ANTHROPIC_API_KEY in the environment.", file=sys.stderr)
        sys.exit(2)

    schema = _load_invoice_extraction_schema()
    InvoiceExtraction = schema.InvoiceExtraction

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    def extract(invoice):
        if input_mode == "document":
            # Native Claude document block: no OCR pre-pass.
            import base64

            pdf_path = REPO_ROOT / "custom_addons" / "invoice_agent" / "tests" / "fixtures" / f"{invoice['id']}.pdf"
            if not pdf_path.exists():
                raise RuntimeError(
                    f"missing fixture PDF for {invoice['id']} — run "
                    "scripts/bench_ocr.py --generate first"
                )
            content = [{
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": base64.b64encode(pdf_path.read_bytes()).decode("ascii"),
                },
            }]
        else:
            content = [{"type": "text", "text": invoice["text"]}]

        response = client.messages.parse(
            model="claude-opus-4-8",
            max_tokens=2048,
            system=prompt_text,
            messages=[{"role": "user", "content": content}],
            output_format=InvoiceExtraction,
        )
        if response.stop_reason == "max_tokens":
            raise RuntimeError("max_tokens reached — run incomplete")
        return response.parsed_output

    return extract


def main():
    parser = argparse.ArgumentParser(description="Evaluate invoice extraction on the golden set.")
    parser.add_argument(
        "--prompt",
        default="custom_addons/invoice_agent/prompts/v1.md",
        help="Path to the prompt file (byte-exact system prompt).",
    )
    parser.add_argument(
        "--input",
        "--mode",
        dest="input_mode",
        choices=["text", "document"],
        default="text",
        help="A/B input mode: OCR text vs native Claude document block.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call Anthropic with the real API key instead of the offline frozen answer.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Optional path for the JSON run record (e.g. runs/v1-text.json).",
    )
    parser.add_argument(
        "--curve",
        default=None,
        metavar="PATH",
        help="Optional CSV path for the threshold curve "
        "(threshold, score_source, auto_approval_rate, error_rate).",
    )
    args = parser.parse_args()

    prompt_text = load_prompt(args.prompt)
    golden = load_golden_set()

    if args.live:
        extractor = live_extractor(prompt_text, args.input_mode)
    else:
        extractor = offline_extractor(prompt_text)

    per_field, rows, latencies_ms = run_eval(extractor, golden)
    overall = print_report(per_field, rows, latencies_ms)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": "claude-opus-4-8",
            "prompt_path": str(Path(args.prompt)),
            "input_mode": args.input_mode,
            "live": args.live,
            **summarize(per_field, rows, latencies_ms),
        }
        out_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        print(f"\nRun record written to {args.out}")

    if args.curve:
        curve_path = Path(args.curve)
        curve_path.parent.mkdir(parents=True, exist_ok=True)
        cal = calibration_block(rows)
        with open(curve_path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "threshold",
                    "score_source",
                    "auto_approval_rate",
                    "error_rate_among_approved",
                    "false_auto_approvals",
                ],
            )
            writer.writeheader()
            for entry in cal["stated_curve"]:
                writer.writerow({**entry, "score_source": "stated"})
            for entry in cal["calibrated_curve"]:
                writer.writerow({**entry, "score_source": "calibrated"})
        print(f"\nThreshold curve written to {args.curve}")

    # Keep the legacy baseline line in docs/performance.md for continuity.
    perf_doc = REPO_ROOT / "docs" / "performance.md"
    baseline_line = (
        f"Eval run ({datetime.now(timezone.utc):%Y-%m-%d}, {args.input_mode}, "
        f"{Path(args.prompt).name}): {overall * 100:.1f}%"
    )
    if perf_doc.exists():
        content = perf_doc.read_text(encoding="utf-8")
        if baseline_line not in content:
            perf_doc.write_text(content.rstrip() + f"\n\n> {baseline_line}\n", encoding="utf-8")

    return 0 if overall >= 0.5 else 1


if __name__ == "__main__":
    sys.exit(main())
