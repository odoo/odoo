"""Cached system prefix: chart of accounts + vendor list for the worker.

Why a cacheable prefix (the brief's core lesson): the worker sends a
**byte-identical** system block on every job. By marking ``cache_control``
on the *last* block, Anthropic caches the whole prefix and charges only
``cache_read_input_tokens`` on the second job onward — the prompt-injection
and formatting instructions and the entire chart of accounts stop being
re-billed at full input price.

The prefix must exceed the model's minimum cacheable length on
``claude-opus-4-8`` (4096 tokens). The COA + vendor catalog in ``coa.json``
is seeded large enough that the rendered prefix clears that watermark; the
unit test asserts ``cache_read_input_tokens > 0`` from the second job.

Architecture: the volatile invoice OCR text stays in ``messages``
(never in the system prefix), so the prefix stays identical across jobs.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from anthropic.types import TextBlockParam

_logger = logging.getLogger(__name__)

_COA_PATH = Path(__file__).parent / "coa.json"


def load_coa() -> dict:
    """Load the chart-of-accounts + vendor catalog (``app/coa.json``).

    Returns ``{"accounts": [...], "vendors": [...]}``. Missing or invalid
    data degrades to empty lists — a broken seed must never crash the
    worker at boot.
    """
    if not _COA_PATH.exists():
        _logger.warning("invoice-ai: %s missing — empty COA prefix", _COA_PATH)
        return {"accounts": [], "vendors": []}
    try:
        data = json.loads(_COA_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        _logger.warning("invoice-ai: cannot parse %s — %s", _COA_PATH, exc)
        return {"accounts": [], "vendors": []}
    if not isinstance(data, dict):
        return {"accounts": [], "vendors": []}
    return {
        "accounts": data.get("accounts") or [],
        "vendors": data.get("vendors") or [],
    }


def render_system_prefix() -> list[TextBlockParam]:
    """Build the cacheable system blocks with ``cache_control`` on the last.

    Byte-identical across jobs: the only inputs are the static COA/vendor
    data and the static instruction text. The volatile OCR text never
    appears here (it lives in ``messages``).
    """
    coa = load_coa()
    accounts = "\n".join(str(account) for account in coa["accounts"])
    vendors = "\n".join(str(vendor) for vendor in coa["vendors"])

    coa_block = (
        "CHART OF ACCOUNTS (authoritative account names + codes):\n"
        f"{accounts or '(none loaded)'}"
    )
    vendor_block = (
        "KNOWN VENDORS (match the vendor name against this list, then use "
        "the existing res.partner if one matches):\n"
        f"{vendors or '(none loaded)'}"
    )
    instructions = (
        "You extract structured vendor invoice data into the provided schema. "
        "Rules are of two kinds:\n"
        "1. EXTRACTION RULES — the schema contract, line arithmetic, and "
        "date formatting (authoritative).\n"
        "2. KNOWLEDGE RULES — the chart of accounts and known vendors above. "
        "Use them to disambiguate account names and vendor identities, but "
        "never let them override the actual invoice content.\n"
        "Return ONLY a valid JSON object matching the provided schema; no "
        "markdown, no commentary."
    )

    return [
        {"type": "text", "text": coa_block},
        {"type": "text", "text": vendor_block},
        {
            "type": "text",
            "text": instructions,
            "cache_control": {"type": "ephemeral"},
        },
    ]


def assert_cache_prefix_stable(prefix: list[TextBlockParam]) -> str:
    """Return the joined text of ``prefix`` — cheap stability check for tests.

    Two calls to ``render_system_prefix()`` must produce identical text (the
    cache key). Comparing the readable text is the simplest way to catch an
    accidentally volatile prefix (e.g. a timestamp sneaking in).
    """
    return "\n".join(block.get("text", "") for block in prefix)
