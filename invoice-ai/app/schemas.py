"""Pydantic schema for structured invoice extraction.

This file is byte-identical in *schema semantics* to
``custom_addons/invoice_agent/models/invoice_extraction.py`` — the shared
contract quoted in docs/openapi.yaml and ADR-003. If one of the two files
changes, the other must change with it; a CI step can diff the JSON Schema
outputs of both to enforce that.

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

Confidence contract (mirrors the addon's week-7 milestone):

* ``field_confidence`` is a nested ``ExtractionFieldConfidence`` object, one
  ``float | None`` per field group (plus ``overall``). It is the model's
  **self-reported** certainty. Values are deliberately unconstrained floats:
  the Odoo side blends them with OCR conf + arithmetic/VAT/IBAN checks in
  ``models/confidence.py``.
* ``notes`` is a free-text ambiguity string the model fills when it is torn
  between values.
"""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class InvoiceLine(BaseModel):
    """A single line item on the vendor invoice.

    ``extra="forbid"`` is what makes pydantic v2 emit
    ``additionalProperties: false`` for this nested object.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    quantity: Decimal
    price_unit: Decimal
    # Line-level confidence is a real Claude output we want to keep, but the
    # model may omit it; it stays optional.
    confidence: float | None = None


class ExtractionFieldConfidence(BaseModel):
    """Per-field-group certainty, self-reported by the model, 0..1."""

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

    Required fields (every real vendor invoice carries them): vendor name,
    invoice date, currency, amount total, and the line items.

    Optional fields (a real invoice genuinely omits them in some layouts):
    vendor VAT, due date, subtotal and tax total.
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


class Usage(BaseModel):
    """Token counters returned next to every extraction.

    Mirrors docs/openapi.yaml ``ExtractionResponse.usage``:
    ``additionalProperties: false`` with four nullable integer counters.
    """

    model_config = ConfigDict(extra="forbid")

    input_tokens: int | None = None
    cache_creation_input_tokens: int | None = None
    cache_read_input_tokens: int | None = None
    output_tokens: int | None = None


class ExtractionResponse(BaseModel):
    """The 200 envelope of ``POST /v1/extract``.

    Matches docs/openapi.yaml ``ExtractionResponse`` exactly: the validated
    extraction, the usage ledger, and the model id. Declared as the route's
    ``response_model`` so the generated OpenAPI actually carries these
    components — a plain-dict return annotation would leave the contract
    schemas out of the spec (the drift check in
    ``scripts/check_openapi_drift.py`` enforces their presence).
    """

    model_config = ConfigDict(extra="forbid")

    extraction: InvoiceExtraction
    usage: Usage
    model: str


class EmbedRequest(BaseModel):
    """Body of ``POST /v1/embed`` — one or more raw documents to embed.

    ``list[str]`` is deliberately unconstrained (no ``min_length`` /
    ``max_items``): batching lives in the embedder, and the contract keeps
    plain types per the project schema rules.
    """

    model_config = ConfigDict(extra="forbid")

    texts: list[str]


class EmbedResponse(BaseModel):
    """200 envelope of ``POST /v1/embed``.

    ``vectors`` is aligned 1:1 with the request texts, each exactly
    ``dimensions`` (1024 for ``voyage-3``) floats. ``dimensions`` is echoed
    so the Odoo side can assert its ``vector(1024)`` column matches the
    model actually deployed.
    """

    model_config = ConfigDict(extra="forbid")

    vectors: list[list[float]]
    model: str
    dimensions: int


class HealthResponse(BaseModel):
    """The 200 envelope of ``GET /healthz``.

    ``status`` is pinned to ``ok`` (the compose healthcheck asserts on it);
    ``build_sha`` is the git SHA stamped at image build time
    (``INVOICE_AI_BUILD_SHA``), defaulting to ``dev`` on local checkouts.
    """

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]
    build_sha: str


def invoice_extraction_json_schema() -> dict:
    """Return the JSON Schema view of ``InvoiceExtraction``.

    Used for the ``output_config={'format': {'type': 'json_schema',
    'schema': ...}}`` JSON path: the schema must exactly match the Odoo-side
    ``invoice_extraction_json_schema()`` — a CI diff enforces it.
    """
    return InvoiceExtraction.model_json_schema()
