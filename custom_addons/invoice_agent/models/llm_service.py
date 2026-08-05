"""LLM service — the only module that touches the Anthropic SDK.

Service contract (mirrors the task brief):
* ``extract_invoice(text)`` runs Structured Outputs via
  ``client.messages.parse(model='claude-opus-4-8', output_format=InvoiceExtraction, ...)``
  and returns the schema-validated ``InvoiceExtraction`` object plus usage.
* ``stop_reason == 'max_tokens'`` raises loudly — a truncated half-record must
  never be persisted as if it were complete.
* The API key lives in ``ir.config_parameter`` (``sudo()``), never in source;
  admins set it from Settings → Invoice Agent. The model id is pinned in one
  place (``ANTHROPIC_MODEL``) so later prompt tuning is one diff.

Import safety (see ``invoice_extraction.py``): on a stale image without
``anthropic``/``pydantic`` the module still loads; the first real call raises
a clear ``UserError`` telling the operator to rebuild the image.
"""

import logging

from odoo import _, api, models
from odoo.exceptions import UserError

from .invoice_extraction import (
    InvoiceExtraction,
    _PYDANTIC_AVAILABLE,
    invoice_extraction_json_schema,
)

_logger = logging.getLogger(__name__)

# Pinned in exactly one place — the single source of truth for LLM config.
ANTHROPIC_MODEL = "claude-opus-4-8"
ANTHROPIC_MAX_TOKENS = 2048
ANTHROPIC_TIMEOUT_SECONDS = 90

ANTHROPIC_KEY_PARAM = "invoice_agent.anthropic_api_key"
ANTHROPIC_MODEL_PARAM = "invoice_agent.anthropic_model"

EXTRACTION_SYSTEM_PROMPT = (
    "You extract vendor invoice data into strict JSON that validates against "
    "the provided JSON schema. Read the invoice text carefully.\n\n"
    "Rules:\n"
    "- vendor_name: the supplier's legal name as printed on the invoice.\n"
    "- vendor_vat: the supplier's VAT / tax registration number. Omit when "
    "the invoice does not print one.\n"
    "- invoice_date: the issue date (YYYY-MM-DD).\n"
    "- due_date: the payment due date (YYYY-MM-DD). Omit when the invoice "
    "does not state one.\n"
    "- currency: the ISO-4217 code (EUR, USD, ...).\n"
    "- subtotal: taxable base before tax. Omit when only the grand total is "
    "printed.\n"
    "- tax_total: total tax / VAT amount. Omit when not stated separately.\n"
    "- amount_total: the grand total the customer must pay.\n"
    "- lines: every line item on the invoice with name, quantity and "
    "price_unit. Preserve the order printed on the invoice.\n\n"
    "Return ONLY the JSON object — no markdown fences, no commentary."
)


class InvoiceLlmService(models.AbstractModel):
    _name = "invoice.llm.service"
    _description = "Single entry point for every Claude call"

    # ------------------------------------------------------------------
    # Client construction
    # ------------------------------------------------------------------
    @api.model
    def _client(self):
        """Build the Anthropic client from the configured API key."""
        if not _PYDANTIC_AVAILABLE:
            raise UserError(
                _(
                    "Structured extraction is disabled: pydantic is not "
                    "installed in the running image. Rebuild it with "
                    "`docker compose build odoo`.",
                ),
            )
        try:
            import anthropic  # only import here — no other module touches the SDK
        except ImportError:
            raise UserError(_("anthropic is not installed — rebuild the odoo image."))
        api_key = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(ANTHROPIC_KEY_PARAM)
        )
        if not api_key:
            raise UserError(
                _(
                    "Anthropic API key is not configured. Set it in Settings → "
                    "Invoice Agent → Anthropic API Key.",
                ),
            )
        return anthropic.Anthropic(
            api_key=api_key,
            timeout=ANTHROPIC_TIMEOUT_SECONDS,
        )

    @api.model
    def _model(self):
        """Admin-overridable model id via the config parameter."""
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(ANTHROPIC_MODEL_PARAM)
            or ANTHROPIC_MODEL
        )

    # ------------------------------------------------------------------
    # Extract
    # ------------------------------------------------------------------
    @api.model
    def extract_invoice(self, text):
        """Run structured extraction against Claude and validate the output.

        :param text: the raw OCR / invoice text
        :return: dict with ``parsed`` (the schema-validated
                 ``InvoiceExtraction`` object), ``usage`` (input/output
                 tokens), ``model`` and ``stop_reason``
        :raises UserError: when the API key is missing, the call fails, or
            the response was truncated (``stop_reason == 'max_tokens'``) —
            a truncated half-record must never be persisted as complete.
        """
        self.ensure_one()
        if not text:
            raise UserError(_("No invoice text to extract."))

        client = self._client()
        model = self._model()
        messages = [
            {
                "role": "user",
                "content": text,
            },
        ]

        # Preferred path (modern SDK): client.messages.parse() validates with
        # the Pydantic model itself and returns response.parsed_output. Older
        # SDKs only expose messages.create() + output_schema= — fall back to
        # that and let pydantic validate the text payload afterwards.
        try:
            response = client.messages.parse(
                model=model,
                max_tokens=ANTHROPIC_MAX_TOKENS,
                system=EXTRACTION_SYSTEM_PROMPT,
                messages=messages,
                output_format=InvoiceExtraction,
            )
            parsed = response.parsed_output
        except TypeError:
            _logger.info(
                "invoice_agent: messages.parse() unavailable, falling back to "
                "output_schema= (model %s)",
                model,
            )
            response = client.messages.create(
                model=model,
                max_tokens=ANTHROPIC_MAX_TOKENS,
                system=EXTRACTION_SYSTEM_PROMPT,
                messages=messages,
                output_schema=invoice_extraction_json_schema(),
            )
            parsed = InvoiceExtraction.model_validate_json(
                response.content[0].text,
            )

        if response.stop_reason == "max_tokens":
            # Never persist a truncated half-record silently: raise loudly so
            # the caller marks the record failed instead of 'extracted'.
            raise UserError(
                _(
                    "Claude stopped because it hit max_tokens during invoice "
                    "extraction — the record is incomplete. Increase "
                    "ANTHROPIC_MAX_TOKENS and retry.",
                ),
            )

        usage = response.usage
        _logger.info(
            "invoice_agent extract_invoice: model=%s input=%s output=%s "
            "stop=%s",
            model,
            getattr(usage, "input_tokens", None),
            getattr(usage, "output_tokens", None),
            response.stop_reason,
        )
        return {
            "parsed": parsed,
            "usage": {
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
            },
            "model": getattr(response, "model", model),
            "stop_reason": response.stop_reason,
        }

    # ------------------------------------------------------------------
    # Compatibility wrapper (legacy suite / scratch scripts)
    # ------------------------------------------------------------------
    @api.model
    def call_claude(self, system_prompt, messages):
        """Thin ``client.messages.create`` wrapper used by early tests.

        Legacy API: returns ``{"content": ..., "usage": {...}}``. New code
        should use :meth:`extract_invoice` (schema-validated) instead; this
        method is kept so ``test_llm_service.py`` and the scratch benchmark
        keep working unchanged.
        """
        client = self._client()
        model = self._model()
        response = client.messages.create(
            model=model,
            max_tokens=1000,
            system=system_prompt,
            messages=messages,
        )
        return {
            "content": response.content[0].text,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        }

    # ------------------------------------------------------------------
    # Raw payload serialization (for ai_extracted_json)
    # ------------------------------------------------------------------
    @api.model
    def extraction_to_dict(self, extraction):
        """Serialize a validated ``InvoiceExtraction`` to a plain dict.

        Decimal / date objects are not JSON-serializable by the ``json``
        module alone — this is the single place that knows how to render them.
        """
        if extraction is None:
            return {}
        payload = extraction.model_dump()
        if "lines" in payload:
            payload["lines"] = [
                dict(
                    line,
                    quantity=float(line["quantity"]),
                    price_unit=float(line["price_unit"]),
                )
                for line in payload["lines"]
            ]
        for key in ("subtotal", "tax_total", "amount_total"):
            if payload.get(key) is not None:
                payload[key] = float(payload[key])
        for key in ("invoice_date", "due_date"):
            if payload.get(key) is not None:
                payload[key] = payload[key].isoformat()
        return payload
