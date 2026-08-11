"""Pydantic schema for structured invoice extraction.

The task brief pins three hard schema rules:

1. ``additionalProperties: false`` *everywhere* — pydantic v2 emits this for
   every model (root + nested) when ``extra="forbid"`` is set on the config.
2. Explicit ``required`` — a field is required unless it has a default or is
   ``Optional[...]``. We mark ``Optional`` **only** where a real vendor
   invoice genuinely omits the field (VAT number, due date, subtotal, tax
   total).
3. No recursion and **no numeric or length constraints** — by design we use
   plain types (``str``, ``date``, ``Decimal``, ``list[...]``) and never add
   ``Field(ge=...)`` / ``max_length`` / ``min_length``. Constraining the
   prompt is the model's job; constraining the schema is not.

Confidence contract (week 7, confidence scoring milestone):

* ``field_confidence`` is a nested ``ExtractionFieldConfidence`` object, one
  ``float | None`` per field group (plus ``overall``). It is the model's
  **self-reported** certainty — exactly the "not log-probs" signal the brief
  asks for. It stays independent from the deterministic cross-checks
  (``models/confidence.py``) so the eval harness can measure whether a
  self-reported 0.95 is actually more often correct than a self-reported
  0.80, and so the stored ``confidence_score`` on ``account.move`` can be a
  documented blend of OCR conf + self-report + arithmetic/VAT/IBAN checks.
* ``notes`` is a free-text ambiguity string the model fills when it is torn
  between values (e.g. "Date line reads 2026-07-01 but TOTAL stamp says
  ‎01/07/2026") — surfaced verbatim on the Needs Review chatter message.

Import safety: ``pydantic`` ships inside the rebuilt odoo image (it is a
transitive dependency of ``anthropic`` and is pinned in requirements.txt).
On a stale image the module still imports — ``InvoiceExtraction`` is replaced
by a placeholder that raises a clear ``UserError`` when used, so the addon
never fails to load because of a missing package.
"""

import logging
from datetime import date
from decimal import Decimal

_logger = logging.getLogger(__name__)

try:
    from pydantic import BaseModel, ConfigDict, Field

    _PYDANTIC_AVAILABLE = True
except ImportError:  # pragma: no cover - only on a stale (un-rebuilt) image
    BaseModel = object  # type: ignore[assignment,misc]
    ConfigDict = dict  # type: ignore[assignment,misc]
    Field = None  # type: ignore[assignment,misc]
    _PYDANTIC_AVAILABLE = False
    _logger.warning(
        "invoice_agent: pydantic is not installed — InvoiceExtraction schema "
        "is disabled. Rebuild the odoo image (docker compose build odoo) so "
        "the extraction pipeline can run.",
    )


class InvoiceLine:
    """Placeholder used when pydantic is unavailable (stale image only)."""

    def __init__(self, *args, **kwargs):
        raise RuntimeError(
            "InvoiceLine is unavailable: pydantic is not installed. "
            "Rebuild the odoo image with `docker compose build odoo`.",
        )


class ExtractionFieldConfidence:
    """Placeholder used when pydantic is unavailable (stale image only)."""

    def __init__(self, *args, **kwargs):
        raise RuntimeError(
            "ExtractionFieldConfidence is unavailable: pydantic is not "
            "installed. Rebuild the odoo image with `docker compose build odoo`.",
        )


class InvoiceExtraction:
    """Placeholder used when pydantic is unavailable (stale image only)."""

    def __init__(self, *args, **kwargs):
        raise RuntimeError(
            "InvoiceExtraction is unavailable: pydantic is not installed. "
            "Rebuild the odoo image with `docker compose build odoo`.",
        )


if _PYDANTIC_AVAILABLE:

    class InvoiceLine(BaseModel):
        """A single line item on the vendor invoice.

        ``extra="forbid"`` is what makes pydantic v2 emit
        ``additionalProperties: false`` for this nested object. No
        ``Field(min/max...)`` constraints — the brief forbids them.
        """

        model_config = ConfigDict(extra="forbid")

        name: str
        quantity: Decimal
        price_unit: Decimal
        # Line-level confidence is a real Claude output we want to keep, but
        # the model may omit it; it is not part of the hand-labelled golden
        # set fields, so it stays optional.
        confidence: float | None = None

    class ExtractionFieldConfidence(BaseModel):
        """Per-field-group certainty, self-reported by the model, 0..1.

        Mirrors ``InvoiceExtraction``'s field groups one-to-one. Each entry is
        optional: the model may state certainty for any subset of groups. The
        deterministic confidence layer (``models/confidence.py``) is what
        actually *uses* these numbers; missing entries simply contribute no
        signal and the layer falls back to OCR conf / cross-checks.

        Values are deliberately unconstrained floats — the brief forbids
        numeric constraints, and the eval harness measures calibration (does
        a self-reported 0.95 beat a self-reported 0.80?) rather than trusting
        the number.
        """

        model_config = ConfigDict(extra="forbid")

        overall: float | None = None
        vendor_name: float | None = None
        vendor_vat: float | None = None
        invoice_date: float | None = None
        due_date: float | None = None
        currency: float | None = None
        subtotal: float | None = None
        tax_total: float | None = None
        amount_total: float | None = None
        lines: float | None = None

    class InvoiceExtraction(BaseModel):
        """The schema-validated structure Claude must fill for each invoice.

        Required (every real vendor invoice carries them): vendor name,
        invoice date, currency, amount total, and the line items.

        Optional (a real invoice genuinely omits them in some layouts):
        vendor VAT, due date (many pro-formas / credit notes omit it),
        subtotal and tax total (some vendors print only the grand total).

        Optional-by-design confidence signals (week 7):
        ``field_confidence`` (one float per field group) and ``notes`` (a
        free-text ambiguity explanation). Both are *advisory* — the stored
        ``confidence_score`` on ``account.move`` is the calibrated blend, not
        these raw numbers.
        """

        model_config = ConfigDict(extra="forbid")

        vendor_name: str
        vendor_vat: str | None = None
        invoice_date: date
        due_date: date | None = None
        currency: str
        subtotal: Decimal | None = None
        tax_total: Decimal | None = None
        amount_total: Decimal
        lines: list[InvoiceLine]
        field_confidence: ExtractionFieldConfidence | None = None
        notes: str | None = None

    def invoice_extraction_json_schema():
        """Return the JSON Schema view of ``InvoiceExtraction``.

        Used for the ``output_config={'format': {'type': 'json_schema',
        'schema': ...}}`` path as well as by the eval script for diffing.
        """
        return InvoiceExtraction.model_json_schema()


def _require_pydantic():
    """Raise a clean error instead of a NameError when pydantic is absent."""
    if not _PYDANTIC_AVAILABLE:
        raise RuntimeError(
            "InvoiceExtraction is unavailable: pydantic is not installed. "
            "Rebuild the odoo image with `docker compose build odoo`.",
        )
