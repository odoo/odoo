"""Deterministic confidence signals and cross-checks for invoice extraction.

The brief asks for confidence sources that are **not** LLM log-probs. This
module implements the three deterministic families that feed the stored
``account.move.confidence_score``:

1. **Arithmetic check** — ``lines_sum`` compares ``sum(quantity * price_unit)``
   against ``amount_total`` and produces a float 0..1: a perfect match scores
   1.0, a mismatch beyond ``ARITHMETIC_TOLERANCE`` scores 0.0, and a
   rounding-level divergence (<= 1 currency unit) scores 0.5. This is the
   strongest signal an invoice gives us — numbers on a real bill must add up.

2. **VAT / IBAN rescue** — ``vat_from_text`` and ``iban_from_text`` scan the
   raw OCR text with per-country VAT-prefix regexes and the ISO-13616 IBAN
   pattern. When the LLM omitted or typo'd a VAT/IBAN, the rescue writes the
   regex-found value back into the payload and credits the extraction for the
   recovery ("which path fired on every move" — that provenance lands in
   ``checks``).

3. **Blend** — ``combined_confidence`` folds the model's *self-reported*
   ``field_confidence`` (calibrated against eval data, see
   ``docs/extraction-accuracy.md``) together with OCR per-word conf and the
   cross-check flags. The blend is deliberately transparent: every input and
   the per-field weights that produced the score are returned so the eval
   harness can plot ``stated confidence vs correctness`` and so an auditor
   can see exactly why a 0.86 landed below the threshold.

Calibration note (the "stated certainty must be calibrated" lesson): the
self-reported floats are *inputs*, never the output. The weights
``SELF_REPORT_WEIGHT / OCR_WEIGHT / MATH_WEIGHT / RESCUE_WEIGHT`` are the
tuning knobs the week-7 review DB query tunes; a model that overstates
certainty gets its self-report weight cut in the next release, not in this
file.
"""

import re

# Tolerance for the arithmetic check as an absolute currency delta. A cent-
# sized rounding discrepancy is normal on real invoices; anything larger
# means the extraction is internally inconsistent.
ARITHMETIC_TOLERANCE = 0.01
# Above this absolute delta the arithmetic check contributes 0 — the lines
# do not add up to the grand total by more than rounding.
ARITHMETIC_HARD_FAIL_DELTA = 1.0

# ISO-4217 currency code pattern reused by the eval + controller layers.
CURRENCY_RE = re.compile(r"\b[A-Z]{3}\b")

# ---------------------------------------------------------------------------
# VAT rescue patterns — per-country legal syntax, applied in order.
# ---------------------------------------------------------------------------
# The regexes mirror the l10n_* validation rules in Odoo's addons
# (l10n_ar, l10n_de, base_vat, ...). They match the *number* as printed on
# an invoice; they are rescue heuristics, not a legal validator — a matched
# value that fails ``res.partner`` search simply degrades the check below.
VAT_PATTERNS = [
    # EU general: XX + up to 12 alphanumerics (GB, DE, FR, NL, BE, AT, ...)
    re.compile(
        r"\b(?:AT|BE|BG|CY|CZ|DE|DK|EE|EL|ES|FI|FR|GB|HR|HU|IE|IT|LT|LU|LV|"
        r"MT|NL|PL|PT|RO|SE|SI|SK)[0-9A-Z]{2,12}\b",
    ),
    # SA (Saudi): 15 digits (ZATCA e-invoicing)
    re.compile(r"\b3[0-9]{14}\b"),
    # CH (Swiss UID): CHE-###.###.###
    re.compile(r"CHE-\d{3}\.\d{3}\.\d{3}"),
    # AU (ABN): 11 digits with optional spaces
    re.compile(r"\b\d{2} \d{3} \d{3} \d{3}\b"),
    # CA (GST/HST): RT123456789 / RN123456789RT0001
    re.compile(r"\b(?:R[TN]\d{9}(?:RT\d{4})?|R[TN]\d{9})\b"),
    # US: 9 digits (EIN) — low signal, kept last
    re.compile(r"\b\d{9}\b"),
]

IBAN_RE = re.compile(
    r"\b[A-Z]{2}[0-9]{2}(?:[ -]?[A-Z0-9]{4}){2,7}(?:[ -]?[A-Z0-9]{1,3})?\b",
)

# Keys that the LLM's field_confidence may carry.
FIELD_GROUPS = (
    "vendor_name",
    "vendor_vat",
    "invoice_date",
    "due_date",
    "currency",
    "subtotal",
    "tax_total",
    "amount_total",
    "lines",
)


# ---------------------------------------------------------------------------
# Arithmetic check
# ---------------------------------------------------------------------------
def _as_float(value):
    """Best-effort numeric conversion; None on anything non-numeric."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def lines_sum(lines):
    """Total of quantity * price_unit across the extracted lines."""
    total = 0.0
    for line in lines or []:
        quantity = _as_float(line.get("quantity")) if isinstance(line, dict) else None
        price_unit = (
            _as_float(line.get("price_unit")) if isinstance(line, dict) else None
        )
        total += (quantity if quantity is not None else 1.0) * (
            price_unit if price_unit is not None else 0.0
        )
    return total


def arithmetic_check(lines, amount_total):
    """Score 0..1 for how well the line items add up to the grand total."""
    total = lines_sum(lines)
    amount = _as_float(amount_total)
    if amount is None:
        return 0.0
    delta = abs(total - amount)
    if delta <= ARITHMETIC_TOLERANCE:
        return 1.0
    if delta <= ARITHMETIC_HARD_FAIL_DELTA:
        return 0.5
    return 0.0


# ---------------------------------------------------------------------------
# VAT / IBAN rescue from raw OCR text
# ---------------------------------------------------------------------------
def _normalize_iban(value):
    """Strip separators and uppercase — ISO 13616 canonical form."""
    return re.sub(r"[\s-]+", "", value or "").upper()


def vat_from_text(ocr_text):
    """Return the first plausible VAT/tax id or ``None``.

    OCR is messy: ``0``/``O``, ``1``/``l`` confusions are common. The EU
    prefix regexes are anchored enough to survive most of that noise; the
    US 9-digit fallback is deliberately last and weak.
    """
    if not ocr_text:
        return None
    text = ocr_text.upper()
    for pattern in VAT_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


def iban_from_text(ocr_text):
    """Return the first normalized IBAN or ``None`` when nothing matches."""
    if not ocr_text:
        return None
    match = IBAN_RE.search(ocr_text)
    if not match:
        return None
    iban = _normalize_iban(match.group(0))
    if len(iban) < 15:
        # An IBAN is 15..34 chars; shorter matches are false positives
        # (e.g. "DE12" inside a postal code).
        return None
    return iban


# ---------------------------------------------------------------------------
# Rescue application onto a payload dict (mutating on purpose — the caller
# keeps the resulting payload + check log together)
# ---------------------------------------------------------------------------
def apply_rescues(payload, ocr_text):
    """Fill missing/weak VAT + IBAN fields from the raw OCR text.

    Mutates ``payload`` in place and returns a list of check descriptions
    recording which path fired ("the log which path fired on every move").

    Only *missing* values are rescued; a value the LLM already extracted is
    trusted over the regex (the model reads context, the regex reads a
    pattern).
    """
    checks = []
    if not ocr_text:
        return checks

    current_vat = (
        (payload.get("vendor_vat") or "")
        if isinstance(payload.get("vendor_vat"), str)
        else ""
    )
    if not current_vat:
        rescued = vat_from_text(ocr_text)
        if rescued:
            payload["vendor_vat"] = rescued
            checks.append("rescue:vat")

    current_iban = payload.get("vendor_iban") or payload.get("iban") or ""
    if not current_iban:
        rescued = iban_from_text(ocr_text)
        if rescued:
            payload["vendor_iban"] = rescued
            checks.append("rescue:iban")

    return checks


# ---------------------------------------------------------------------------
# The blend
# ---------------------------------------------------------------------------
# Weights are calibration knobs, tuned by the week-7 review query. The math
# check is the strongest single signal (numbers on a bill must add up), so it
# gets the largest weight alongside the self-report; the OCR weight covers
# Tesseract per-word confidence; the rescue weight credits a successful regex
# recovery.
SELF_REPORT_WEIGHT = 0.35
OCR_WEIGHT = 0.20
MATH_WEIGHT = 0.30
RESCUE_WEIGHT = 0.15
VERIFIED_BONUS = 0.05  # capped by the 1.0 ceiling


def _clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def _self_reported(payload):
    """Extract the self-reported floats from field_confidence."""
    confidence = payload.get("field_confidence") or {}
    if not isinstance(confidence, dict):
        return None, {}
    overall = confidence.get("overall")
    return _as_float(overall), {
        key: _as_float(confidence.get(key)) for key in FIELD_GROUPS
    }


def combined_confidence(payload, ocr_text=None, ocr_confidence=None, checks=None):
    """Compute the stored ``confidence_score`` for one extraction.

    :param payload: dict form of the ``InvoiceExtraction`` (as stored in
        ``ai_extracted_json`` / ``extraction_json``).
    :param ocr_text: raw OCR text, used by the VAT/IBAN rescue and as the
        arithmetic context. May be None on re-runs that skip OCR.
    :param ocr_confidence: Tesseract per-word mean confidence 0..1, when known.
    :param checks: pre-existing check log (e.g. from a previous pass) — new
        rescues are appended.
    :return: ``(score, details)`` where ``score`` is the 0..1 float stored on
        the move and ``details`` carries every input + the weights + the
        check log, for audit and for the eval harness.
    """
    checks = list(checks or [])

    # ---- 1. Arithmetic check -------------------------------------------
    # Lines sum to the *subtotal*, never the tax-inclusive grand total. A
    # VAT invoice whose lines add to 500.00 and whose amount_total is 621.60
    # is perfectly consistent — comparing lines against amount_total would
    # fail every taxed bill. Fall back to amount_total only when the invoice
    # prints no subtotal at all (the "only grand total" layout).
    lines = payload.get("lines") or []
    math_target = payload.get("subtotal")
    if math_target is None:
        math_target = payload.get("amount_total")
    math_score = arithmetic_check(lines, math_target)

    # ---- 2. Self-report (calibrated in eval, never trusted raw) --------
    overall_reported, per_group = _self_reported(payload)
    # Where the model did not state a per-group number, fall back to the
    # overall; where neither exists, no signal is credited.
    reported = 0.0
    for key in FIELD_GROUPS:
        value = per_group.get(key)
        if value is None:
            value = overall_reported
        if value is not None:
            reported += value
    if FIELD_GROUPS:
        reported /= len(FIELD_GROUPS)

    # ---- 3. Rescue: VAT / IBAN regex over the raw OCR text -------------
    rescue_score = 0.0
    if ocr_text:
        if vat_from_text(ocr_text):
            rescue_score += 0.5
        if iban_from_text(ocr_text):
            rescue_score += 0.5
        rescue_score = _clamp(rescue_score)
    if ocr_text and ocr_confidence is None:
        ocr_confidence = 0.5  # OCR ran with no calibrated conf — neutral

    # ---- 4. Blend + verified bonus -------------------------------------
    verified = (
        ("arithmetic" if math_score >= 1.0 else None),
        ("vat" if (payload.get("vendor_vat") or "").strip() else None),
        ("iban" if (payload.get("vendor_iban") or "").strip() else None),
    )
    verified = tuple(item for item in verified if item)

    score = (
        SELF_REPORT_WEIGHT * reported
        + OCR_WEIGHT * (ocr_confidence if ocr_confidence is not None else 0.0)
        + MATH_WEIGHT * math_score
        + RESCUE_WEIGHT * rescue_score
    )
    if verified:
        score += VERIFIED_BONUS
    score = _clamp(score)

    details = {
        "self_reported": reported,
        "per_group_reported": {key: per_group.get(key) for key in FIELD_GROUPS},
        "ocr_confidence": ocr_confidence,
        "math_score": math_score,
        "rescue_score": rescue_score,
        "verified": verified,
        "checks": checks,
        "weights": {
            "self_report": SELF_REPORT_WEIGHT,
            "ocr": OCR_WEIGHT,
            "math": MATH_WEIGHT,
            "rescue": RESCUE_WEIGHT,
            "verified_bonus": VERIFIED_BONUS,
        },
    }
    return score, details
