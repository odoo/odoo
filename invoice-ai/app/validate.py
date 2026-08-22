"""RAG validation module — cached prefix, volatile suffix prompt design.

After extraction (``InvoiceExtraction``) and retrieval
(``retrieve_vendor_context``), this module sends the extraction plus the
vendor's historical context to Claude for validation.  The prompt is split
into a **cached prefix** (chart of accounts + vendor history + validation
instructions — identical across invoices for the same vendor) and a
**volatile suffix** (this invoice's extraction — changes per call).

``cache_control`` sits on the last block of the prefix.  Any byte change
downstream invalidates the cache, so the volatile extraction data comes
AFTER the cached blocks.  The prefix must be >= 4096 tokens on
``claude-opus-4-8`` before reads register; the COA + 8 retrieved bills
typically exceed that watermark.

Flow (called by the consumer after extract + retrieve)::

    validate_extraction(
        extraction=extraction,
        vendor_context=retrieved_context,
        ocr_text=ocr_text,
    )
    -> ValidationVerdict  (structured output via messages.parse)
"""

from __future__ import annotations

import logging
from typing import Any

from anthropic import (
    APIConnectionError,
    APIStatusError,
    AsyncAnthropic,
)
from anthropic.types import CacheControlEphemeralParam, TextBlockParam

from .config import settings
from .schemas import (
    Citation,
    InvoiceExtraction,
    ValidationVerdict,
)

_logger = logging.getLogger(__name__)

CACHE_CONTROL: CacheControlEphemeralParam = {"type": "ephemeral"}


def _build_validation_system_blocks(
    coa_text: str,
    vendor_history: str,
    gl_frequencies: str,
) -> list[TextBlockParam]:
    """Build the cacheable system prefix for validation.

    The prefix contains:
    1.  Chart of accounts (authoritative account names + codes).
    2.  Vendor history (retrieved bills with their GL codes).
    3.  GL account frequency distribution for this vendor.
    4.  Validation instructions + the ``ValidationVerdict`` schema hint.

    ``cache_control`` on the last block marks the whole prefix cacheable.
    The volatile extraction text goes in ``messages``, not here.
    """
    from .system_prefix import load_coa

    if not coa_text:
        coa = load_coa()
        accounts = "\n".join(str(a) for a in coa["accounts"])
        coa_text = accounts or "(none loaded)"

    validation_rules = (
        "You validate a vendor invoice extraction against the vendor's "
        "historical posting patterns.  For each extraction you must decide:\n"
        "1. account_id: the most likely GL account code from the chart of "
        "accounts above, based on what this vendor historically posts to "
        "(see the frequency distribution and history).\n"
        "2. account_confidence: your certainty for the account assignment "
        "(float 0..1).  High when the vendor always posts to the same "
        "account; low when the vendor uses multiple accounts for similar "
        "items.\n"
        "3. amount_plausible: whether the invoice amounts are consistent "
        "with the vendor's historical amounts (True/False).\n"
        "4. evidence: a NON-EMPTY list of citations linking your verdict to "
        "specific retrieved historical bills.  Each citation must include:\n"
        "   - move_id: the move_id of the historical bill (must be one of "
        "the bill IDs shown in VENDOR HISTORY above — never invent an ID).\n"
        "   - quoted_line: a short excerpt from that bill's content that "
        "supports your verdict (copy verbatim from the history).\n"
        "   - reasoning: why this historical bill supports your account "
        "assignment or plausibility judgment.\n"
        "   You MUST provide at least one citation.  If the vendor has no "
        "history, cite the absence explicitly with move_id=0.\n"
        "5. duplicate_of_move_id: if the extraction's ref or amounts "
        "match a historical bill exactly, return that bill's move_id. "
        "Otherwise null.\n"
        "6. flags: any warnings — 'unusual_amount' (amount > 2× the "
        "vendor's average), 'no_history' (vendor has < 3 historical "
        "bills), 'low_account_confidence' (account_confidence < 0.5).\n"
        "7. reasoning: a short explanation of your verdict.\n\n"
        "CRITICAL: Every citation's move_id MUST appear in the VENDOR "
        "HISTORY section above.  The system rejects hallucinated IDs.\n\n"
        "Return ONLY a valid JSON object matching the provided schema; no "
        "markdown, no commentary."
    )

    return [
        {"type": "text", "text": f"CHART OF ACCOUNTS:\n{coa_text}"},
        {
            "type": "text",
            "text": f"VENDOR HISTORY:\n{vendor_history or '(no history)'}",
        },
        {
            "type": "text",
            "text": f"GL ACCOUNT FREQUENCIES:\n{gl_frequencies or '(none)'}",
        },
        {
            "type": "text",
            "text": validation_rules,
            "cache_control": CACHE_CONTROL,
        },
    ]


def _format_vendor_history(candidates: list[dict[str, Any]]) -> str:
    """Format candidate bills into a readable history block.

    Includes ``rerank_score`` when present (two-stage retrieval).
    The move_id is prominently displayed so the model can reference it
    in its citations — the code guard later verifies every cited ID
    actually appears here.
    """
    if not candidates:
        return "(no historical bills found)"
    parts = []
    for i, bill in enumerate(candidates, 1):
        content = bill.get("content", "")
        distance = bill.get("distance", 0.0)
        move_id = bill.get("move_id", 0)
        rerank = bill.get("rerank_score")
        similarity = 1.0 - distance
        header = f"[Bill {i}] move_id={move_id} similarity={similarity:.3f}"
        if rerank is not None:
            header += f" rerank_score={rerank:.3f}"
        parts.append(f"{header}\n{content}")
    return "\n\n".join(parts)


def _validate_citations(
    verdict: ValidationVerdict,
    retrieved_ids: set[int],
) -> ValidationVerdict:
    """Reject any verdict whose cited move_id is not in the retrieved set.

    This is the anti-hallucination code guard: if Claude invents a bill
    ID that wasn't in the retrieved candidate list, the citation is
    stripped and the verdict is flagged.  A verdict with *no* valid
    citations and no explicit ``move_id=0`` absence marker gets a
    ``no_history`` flag added.

    Returns the (possibly sanitized) verdict.
    """
    valid_citations: list[Citation] = []
    hallucinated: list[int] = []
    for citation in verdict.evidence:
        # move_id=0 is the explicit "no history" marker per the prompt
        if citation.move_id == 0:
            valid_citations.append(citation)
            continue
        if citation.move_id in retrieved_ids:
            valid_citations.append(citation)
        else:
            hallucinated.append(citation.move_id)
            _logger.warning(
                "validate citation guard: hallucinated move_id=%d "
                "not in retrieved set %s — stripping",
                citation.move_id,
                sorted(retrieved_ids),
            )
    verdict.evidence = valid_citations
    if hallucinated:
        hallucinated_flag = f"hallucinated_citation:{','.join(str(m) for m in hallucinated)}"
        if hallucinated_flag not in verdict.flags:
            verdict.flags = list(verdict.flags) + [hallucinated_flag]
    if not verdict.evidence:
        _logger.warning(
            "validate citation guard: no valid citations in verdict — adding no_history flag"
        )
        if "no_history" not in verdict.flags:
            verdict.flags = list(verdict.flags) + ["no_history"]
    return verdict


def _format_gl_frequencies(frequencies: dict[str, int]) -> str:
    """Format GL frequency distribution into a readable block."""
    if not frequencies:
        return "(none)"
    total = sum(frequencies.values())
    lines = []
    for code, count in frequencies.items():
        pct = (count / total * 100) if total else 0
        lines.append(f"  {code}: {count} times ({pct:.0f}%)")
    return "\n".join(lines)


def _format_extraction_for_validation(extraction: InvoiceExtraction) -> str:
    """Format the extraction as the volatile suffix block."""
    lines_text = ""
    if extraction.lines:
        line_parts = []
        for line in extraction.lines:
            line_parts.append(f"  - {line.name}: qty={line.quantity} unit_price={line.price_unit}")
        lines_text = "\n".join(line_parts)

    parts = [
        f"VENDOR: {extraction.vendor_name}",
        f"VAT: {extraction.vendor_vat or '(none)'}",
        f"DATE: {extraction.invoice_date}",
        f"CURRENCY: {extraction.currency}",
        f"AMOUNT_TOTAL: {extraction.amount_total}",
    ]
    if extraction.subtotal is not None:
        parts.append(f"SUBTOTAL: {extraction.subtotal}")
    if extraction.tax_total is not None:
        parts.append(f"TAX_TOTAL: {extraction.tax_total}")
    if lines_text:
        parts.append(f"LINES:\n{lines_text}")
    if extraction.notes:
        parts.append(f"NOTES: {extraction.notes}")

    return "\n".join(parts)


async def validate_extraction(
    *,
    extraction: InvoiceExtraction,
    vendor_context: dict[str, Any],
    ocr_text: str = "",
    client: AsyncAnthropic | None = None,
    coa_text: str = "",
) -> dict[str, Any]:
    """Validate an extraction against vendor history.

    Sends the cached-prefix + volatile-suffix prompt to Claude and returns
    a ``ValidationVerdict`` via ``messages.parse``.

    :param extraction: the validated extraction from the extract step.
    :param vendor_context: output of ``retrieve_vendor_context`` —
        ``{candidates, gl_account_frequencies}``.
    :param ocr_text: raw OCR text (included for reference in the prompt).
    :param client: injectable ``AsyncAnthropic`` for testing.
    :param coa_text: override the COA text (default from ``coa.json``).
    :return: dict with ``verdict`` (``ValidationVerdict``), ``usage``, ``model``.
    """
    if client is None:
        client = AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            timeout=settings.anthropic_timeout_seconds,
            max_retries=settings.anthropic_max_retries,
        )

    # --- Build the cached prefix ---
    candidates = vendor_context.get("candidates") or []
    frequencies = vendor_context.get("gl_account_frequencies") or {}

    vendor_history = _format_vendor_history(candidates)
    gl_freq_text = _format_gl_frequencies(frequencies)

    system_blocks = _build_validation_system_blocks(
        coa_text=coa_text,
        vendor_history=vendor_history,
        gl_frequencies=gl_freq_text,
    )

    # --- Build the volatile suffix (extraction + OCR text) ---
    extraction_text = _format_extraction_for_validation(extraction)
    user_content = (
        f"EXTRACTION TO VALIDATE:\n{extraction_text}\n\n"
        f"ORIGINAL OCR TEXT:\n{ocr_text or '(not provided)'}"
    )

    # --- Call Claude with structured output ---
    message: Any = None
    verdict: ValidationVerdict | None = None

    try:
        message = await client.messages.parse(
            model=settings.anthropic_model,
            max_tokens=1024,
            system=system_blocks,
            messages=[{"role": "user", "content": user_content}],
            output_format=ValidationVerdict,
        )
        verdict = message.parsed_output
    except TypeError:
        # Older SDK fallback — use messages.create with json_schema
        _logger.info("messages.parse unavailable for validation; using json_schema")
        json_schema = ValidationVerdict.model_json_schema()
        message = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1024,
            system=system_blocks,
            messages=[{"role": "user", "content": user_content}],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": json_schema,
                }
            },
        )
        content_text = "".join(getattr(block, "text", "") for block in message.content)
        verdict = ValidationVerdict.model_validate_json(content_text)
    except (APIStatusError, APIConnectionError) as exc:
        _logger.warning("validation Claude call failed: %s", exc)
        raise

    if verdict is None:
        raise ValueError("Failed to parse ValidationVerdict from response")

    usage = {
        "input_tokens": (getattr(message.usage, "input_tokens", None) if message else None),
        "cache_creation_input_tokens": (
            getattr(
                message.usage,
                "cache_creation_input_tokens",
                None,
            )
            if message
            else None
        ),
        "cache_read_input_tokens": (
            getattr(
                message.usage,
                "cache_read_input_tokens",
                None,
            )
            if message
            else None
        ),
        "output_tokens": (getattr(message.usage, "output_tokens", None) if message else None),
    }

    # --- Citation guard: reject hallucinated move_ids ---
    retrieved_ids = {c["move_id"] for c in candidates if c.get("move_id")}
    verdict = _validate_citations(verdict, retrieved_ids)

    _logger.info(
        "validate: account=%s confidence=%.2f plausible=%s dup=%s "
        "flags=%s citations=%d cache_read=%s",
        verdict.account_id,
        verdict.account_confidence,
        verdict.amount_plausible,
        verdict.duplicate_of_move_id,
        verdict.flags,
        len(verdict.evidence),
        usage.get("cache_read_input_tokens"),
    )

    return {
        "verdict": verdict,
        "usage": usage,
        "model": (
            getattr(message, "model", settings.anthropic_model)
            if message
            else settings.anthropic_model
        ),
        "reranked": vendor_context.get("reranked", False),
        "rerank_model": vendor_context.get("rerank_model", ""),
    }
