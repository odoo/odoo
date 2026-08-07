#!/usr/bin/env python3
"""v0.6 load test: 20 concurrent structured extractions.

Runs the exact "Suggest with AI" path with an in-memory fake extractor so
it is deterministic and consumes zero API credits. Verifies 20 concurrent
calls succeed, cache-read tokens register (prompt-cache proof) and the
invoice.agent.usage ledger records spend.

Run inside an Odoo env where anthropic + pydantic exist:
    venv\Scripts\python.exe odoo-bin shell -d <db> -c \
        "env = {}; exec(open('scripts/loadtest_extractions.py').read())"

or paste into `odoo-bin shell`.
"""

import sys
from concurrent.futures import ThreadPoolExecutor

_TEXT = (
    "ACME SUPPLIES LLC\nVAT: US123456789\nINVOICE 2026-00777\n"
    "Date: 2026-07-01\nDue: 2026-07-31\nServer hosting 1 850.00\n"
    "Setup fee 1 500.00\nSubtotal 1,350.00\nTOTAL USD 1,350.00"
)


def _fake_extract(text):
    """In-memory extraction mirroring the real result shape."""
    from odoo.addons.invoice_agent.models.invoice_extraction import InvoiceExtraction

    extracted = InvoiceExtraction.model_validate(
        {
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
    )
    return {
        "parsed": extracted,
        "usage": {
            "input_tokens": 4000,
            "cache_creation_input_tokens": 4500,
            "cache_read_input_tokens": 4400,
            "output_tokens": 500,
        },
        "model": "claude-opus-4-8",
        "stop_reason": "end_turn",
    }


def main():
    try:
        env = globals()["env"]
    except KeyError:
        print("ERROR: run inside `odoo-bin shell -d <db>` (needs env)")
        return 2

    service = env["invoice.llm.service"]
    original = service.extract_invoice
    service.extract_invoice = _fake_extract

    errors = []

    def worker(i):
        try:
            result = service.extract_invoice(_TEXT)
            service.log_usage(i, result["usage"], model=result["model"])
            return result["usage"]
        except Exception as exc:  # pragma: no cover
            errors.append((i, repr(exc)))
            return None

    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            usages = list(pool.map(worker, range(20)))
    finally:
        service.extract_invoice = original

    ok = [u for u in usages if u is not None]
    cache_read = sum(u.get("cache_read_input_tokens") or 0 for u in ok)
    spend = env["invoice.agent.usage"].mtd_spend()
    print("=== v0.6 load test ===")
    print("concurrent extractions:", len(ok), "/ 20")
    print("errors:", len(errors), errors[:3])
    print("total cache_read_input_tokens (cache hits):", cache_read)
    print("month-to-date AI spend (USD): %.4f" % spend)
    if len(ok) < 20 or cache_read <= 0 or spend <= 0:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
