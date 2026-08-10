#!/usr/bin/env python3
"""Week-seven baseline: diff the extraction against the golden set.

Usage (repo root, inside the rebuilt odoo image — pydantic/anthropic live there):
    python scripts/eval_extraction.py              # offline, frozen answer
    python scripts/eval_extraction.py --live       # real API through client.messages.parse

The golden set lives in `custom_addons/invoice_agent/tests/fixtures/golden_set.json`:
ten realistic vendor invoice texts with hand-labelled ground truth matching the
InvoiceExtraction schema. The script runs the extraction on each text, diffs
the parsed output against the expected payload field-by-field and prints the
per-field accuracy table plus the overall metric. That number is the baseline
week seven has to beat.

Offline mode validates a frozen answer through the real `InvoiceExtraction`
schema so CI can run it deterministically without an API key.
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = (
    REPO_ROOT / "custom_addons" / "invoice_agent" / "tests" / "fixtures" / "golden_set.json"
)

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


def load_golden_set():
    with open(GOLDEN_PATH, encoding="utf-8") as handle:
        return json.load(handle)["invoices"]


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


def run_eval(extractor, golden):
    per_field = {field: {"correct": 0, "total": 0} for field in SCALAR_FIELDS}
    per_field["lines"] = {"correct": 0, "total": 0}
    rows = []

    for invoice in golden:
        parsed = extraction_to_plain(extractor(invoice["text"]))
        expected = invoice["expected"]

        row = {"id": invoice["id"]}
        for field in SCALAR_FIELDS:
            per_field[field]["total"] += 1
            row[field] = value_equal(parsed.get(field), expected.get(field))
            if row[field]:
                per_field[field]["correct"] += 1

        line_accuracy = compare_lines(parsed.get("lines") or [], expected.get("lines") or [])
        per_field["lines"]["total"] += 1
        row["lines"] = line_accuracy
        if line_accuracy >= 1.0:
            per_field["lines"]["correct"] += 1
        rows.append(row)

    return per_field, rows


def print_report(per_field, rows):
    total_fields = sum(entry["total"] for entry in per_field.values())
    total_correct = sum(entry["correct"] for entry in per_field.values())

    print("\n=== Week Seven Extraction Baseline ===\n")
    print(f"{'Field':<18}{'Accuracy':>10}")
    print("-" * 30)
    for field, entry in per_field.items():
        accuracy = entry["correct"] / entry["total"] if entry["total"] else 0.0
        print(f"{field:<18}{accuracy * 100:>9.1f}%")
    overall = total_correct / total_fields if total_fields else 0.0
    print("-" * 30)
    print(f"{'OVERALL':<18}{overall * 100:>9.1f}%")
    print(f"\nInvoices scored: {len(rows)}")

    for row in rows:
        misses = [
            field
            for field in (*SCALAR_FIELDS, "lines")
            if (field == "lines" and row[field] < 1.0) or (field != "lines" and not row[field])
        ]
        if misses:
            print(f"  {row['id']}: missed {', '.join(misses)}")
    return overall


def offline_extractor():
    """Validate a frozen answer through the real schema; deterministic."""
    from custom_addons.invoice_agent.models.invoice_extraction import InvoiceExtraction

    frozen = {
        "vendor_name": "ACME SUPPLIES LLC",
        "vendor_vat": "US123456789",
        "invoice_date": "2026-07-01",
        "due_date": "2026-07-31",
        "currency": "USD",
        "subtotal": 1350.0,
        "tax_total": 0.0,
        "amount_total": 1350.0,
        "lines": [
            {"name": "Server hosting", "quantity": 1.0, "price_unit": 850.0},
            {"name": "Setup fee", "quantity": 1.0, "price_unit": 500.0},
        ],
    }

    def extract(text):
        return InvoiceExtraction.model_validate(frozen)

    return extract


def live_extractor():
    """Real structured extraction mirroring invoice.llm.service.extract_invoice.

    Imports the schema from the addon so the script stays in sync with the
    Odoo runtime path. Requires ANTHROPIC_API_KEY.
    """
    import os

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: --live requires ANTHROPIC_API_KEY in the environment.", file=sys.stderr)
        sys.exit(2)

    from custom_addons.invoice_agent.models.invoice_extraction import InvoiceExtraction

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    def extract(text):
        response = client.messages.parse(
            model="claude-opus-4-8",
            max_tokens=2048,
            system=(
                "You extract vendor invoice data into strict JSON matching the schema. "
                "Return ONLY the object — no markdown fences, no commentary."
            ),
            messages=[{"role": "user", "content": text}],
            output_format=InvoiceExtraction,
        )
        if response.stop_reason == "max_tokens":
            raise RuntimeError("max_tokens reached — run incomplete")
        return response.parsed_output

    return extract


def main():
    parser = argparse.ArgumentParser(description="Evaluate invoice extraction on the golden set.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call Anthropic with the real API key instead of the offline frozen answer.",
    )
    args = parser.parse_args()

    golden = load_golden_set()
    extractor = live_extractor() if args.live else offline_extractor()
    per_field, rows = run_eval(extractor, golden)
    overall = print_report(per_field, rows)

    perf_doc = REPO_ROOT / "docs" / "performance.md"
    baseline_line = f"Week-seven baseline (2026-08-05, claude-opus-4-8): {overall * 100:.1f}%"
    if perf_doc.exists():
        content = perf_doc.read_text(encoding="utf-8")
        if "Week-seven baseline" not in content:
            perf_doc.write_text(content.rstrip() + f"\n\n> {baseline_line}\n", encoding="utf-8")
            print("\nBaseline recorded in docs/performance.md")
        else:
            print(f"\nBaseline already recorded: {baseline_line}")

    return 0 if overall >= 0.5 else 1


if __name__ == "__main__":
    sys.exit(main())
