"""LLM service â€” the only module that touches the Anthropic SDK.

Service contract (v0.6 hardening):

* ``extract_invoice(text)`` runs Structured Outputs via
  ``client.messages.parse(model='claude-opus-4-8', output_format=InvoiceExtraction, ...)``
  and returns the schema-validated ``InvoiceExtraction`` object plus usage.
* ``_call_claude`` is the single choke point for every HTTP call and catches
  the SDK exception hierarchy **most-specific-first** so each failure maps to
  a distinct, accountant-readable ``UserError``:
    ``NotFoundError``       -> "model id is wrong / retired â€” call IT"
    ``RateLimitError``      -> "we are being rate-limited â€” retry after Ns"
    ``APIStatusError``      -> "Claude API error <status> â€” call IT"
    ``APIConnectionError``  -> "could not reach Anthropic â€” try again"
  Every SDK exception is a subclass of ``APIError``; catching the leaf types
  first means a 429 is never mislabelled as a generic status error.
* Prompt caching: the frozen instructions plus a rendered chart-of-accounts
  block go into ``system=[{"type": "text", ..., "cache_control": {"type":
  "ephemeral"}}]`` (``cache_control`` on the **last** block marks the whole
  prefix cacheable). The volatile invoice text stays last in ``messages`` so
  the cacheable prefix is byte-identical across calls â€” a single byte change
  in the prefix invalidates the cache, and the prefix must be >= 4096 tokens
  on ``claude-opus-4-8`` before cache reads register.
* ``stop_reason == 'max_tokens'`` raises loudly â€” a truncated half-record must
  never be persisted as if it were complete.
* Usage (including ``cache_read_input_tokens`` / ``cache_creation_input_tokens``)
  is returned to callers and persisted by ``log_usage`` into
  ``invoice.agent.usage``.
* The API key lives in ``ir.config_parameter`` (``sudo()``), never in source.
  The model id is pinned in one place (``ANTHROPIC_MODEL``).

Import safety (see ``invoice_extraction.py``): on a stale image without
``anthropic``/``pydantic`` the module still loads; the first real call raises
a clear ``UserError`` telling the operator to rebuild the image.

SDK behaviour studied for this rewrite:
* ``anthropic.Anthropic()`` defaults to ``max_retries=2`` â€” the SDK already
  retries idempotent 429/408/5xx transparently before our handler ever sees a
  ``RateLimitError``/``APIStatusError``. We pass ``max_retries`` explicitly so
  the policy is visible and tunable in one place.
* ``RateLimitError`` is a subclass of ``APIStatusError``; ``APIConnectionError``
  is a sibling branch (transport/connection failures, no HTTP status). The
  ``Retry-After`` header (seconds or HTTP-date) lives on
  ``exc.response.headers``.
* Prompt caching is opt-in per content block via ``cache_control``; usage
  reports ``cache_creation_input_tokens`` (cache write) and
  ``cache_read_input_tokens`` (cache hit) alongside ``input_tokens``.
"""

import email.utils
import logging
from datetime import datetime, timezone

from odoo import _, api, models
from odoo.exceptions import UserError

from .invoice_extraction import (
    InvoiceExtraction,
    _PYDANTIC_AVAILABLE,
    invoice_extraction_json_schema,
)

_logger = logging.getLogger(__name__)

# Pinned in exactly one place â€” the single source of truth for LLM config.
ANTHROPIC_MODEL = "claude-opus-4-8"
ANTHROPIC_MAX_TOKENS = 2048
ANTHROPIC_TIMEOUT_SECONDS = 90
# The SDK's default retry policy: 2 automatic retries on idempotent
# 429/408/5xx responses before an exception surfaces to the caller. Passed
# explicitly so the policy is visible and tunable in exactly one place.
ANTHROPIC_MAX_RETRIES = 2

ANTHROPIC_KEY_PARAM = "invoice_agent.anthropic_api_key"
ANTHROPIC_MODEL_PARAM = "invoice_agent.anthropic_model"

# Cache-control marker for prompt caching (see module docstring).
CACHE_CONTROL = {"type": "ephemeral"}

# ---------------------------------------------------------------------------
# Claude Opus 4 pricing, per 1M tokens (USD) â€” used by the usage ledger.
# Cache write is what a cold prefix costs on first call; cache read is a hit.
# These figures are the week-seven cost baseline quoted in the release notes.
# ---------------------------------------------------------------------------
OPUS_PRICE_PER_MT_INPUT = 15.0
OPUS_PRICE_PER_MT_CACHE_WRITE = 3.75
OPUS_PRICE_PER_MT_CACHE_READ = 1.5
OPUS_PRICE_PER_MT_OUTPUT = 75.0

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
    "Return ONLY the JSON object â€” no markdown fences, no commentary."
)

# Minimum cacheable prefix length for prompt caching on claude-opus-4-8.
# Below this, Anthropic does not cache the prefix and usage shows no
# cache_read_input_tokens on the second call.
ANTHROPIC_MIN_CACHEABLE_PREFIX_TOKENS = 4096


def extract_retry_after_seconds(exc):
    """Read the ``Retry-After`` header from a RateLimitError.

    Anthropic sends either a plain integer (seconds) or an HTTP-date.
    Returns an int >= 1 when parseable, else ``None`` so the caller can
    fall back to a sensible default message.
    """
    response = getattr(exc, "response", None)
    if response is None:
        return None
    value = response.headers.get("Retry-After")
    if not value:
        return None
    try:
        return max(1, int(float(value)))
    except (TypeError, ValueError):
        pass
    try:
        retry_at = email.utils.parsedate_to_datetime(value)
        delta = retry_at - datetime.now(timezone.utc)
        return max(1, int(delta.total_seconds()))
    except (TypeError, ValueError):
        return None


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
            import anthropic  # only import here â€” no other module touches the SDK
        except ImportError:
            raise UserError(_("anthropic is not installed â€” rebuild the odoo image."))
        api_key = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(ANTHROPIC_KEY_PARAM)
        )
        if not api_key:
            raise UserError(
                _(
                    "Anthropic API key is not configured. Set it in Settings â†’ "
                    "Invoice Agent â†’ Anthropic API Key.",
                ),
            )
        return anthropic.Anthropic(
            api_key=api_key,
            timeout=ANTHROPIC_TIMEOUT_SECONDS,
            max_retries=ANTHROPIC_MAX_RETRIES,
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
    # Prompt-caching helpers
    # ------------------------------------------------------------------
    @api.model
    def _company(self):
        """Resolve the company for the COA block (context wins, else env)."""
        company_id = self.env.context.get("company_id")
        if company_id:
            return self.env["res.company"].browse(company_id).exists()
        return self.env.company

    @api.model
    def _chart_of_accounts_block(self):
        """Render the chart of accounts as a frozen text block.

        This block is the second half of the cacheable system prefix. It must
        be byte-identical between calls for the prompt cache to hit â€” the COA
        only changes when accounting reconfigures, which is exactly the
        "frozen, rarely-changing" shape the cache wants. When no chart is
        loaded (fresh DB), emit a stable one-line placeholder instead.
        """
        company = self._company()
        accounts = (
            self.env["account.account"]
            .sudo()
            .search(
                [("company_ids", "in", company.ids)],
                order="code",
            )
        )
        if not accounts:
            return "CHART OF ACCOUNTS: not loaded for company %s." % company.name
        lines = ["CHART OF ACCOUNTS (reference only â€” do not invent codes):"]
        for account in accounts:
            lines.append(
                "- %s %s [%s]" % (account.code, account.name, account.account_type),
            )
        return "\n".join(lines)

    @api.model
    def _extraction_system_blocks(self):
        """Build the cacheable system prefix for extraction calls.

        ``cache_control`` is placed on the **last** block â€” Anthropic caches
        the whole prefix up to and including that block. The volatile invoice
        text must therefore live in ``messages``, never in the system prefix,
        or every new invoice would invalidate the cache.
        """
        return [
            {"type": "text", "text": EXTRACTION_SYSTEM_PROMPT},
            {
                "type": "text",
                "text": self._chart_of_accounts_block(),
                # Marks the whole prefix (instructions + COA) as cacheable.
                "cache_control": CACHE_CONTROL,
            },
        ]

    # ------------------------------------------------------------------
    # The one choke point: every Claude call + the exception chain
    # ------------------------------------------------------------------
    @api.model
    def _call_claude(self, system_blocks, messages, max_tokens=None,
                     output_format=None):
        """Run a Messages API call with the hardened error chain.

        :param system_blocks: list of ``{"type": "text", "text": ...}`` blocks
            (may carry ``cache_control`` on the last block).
        :param messages: list of conversation turns; the volatile invoice text
            goes here, AFTER the cacheable system prefix.
        :param max_tokens: response budget (defaults to
            ``ANTHROPIC_MAX_TOKENS``).
        :param output_format: optional pydantic model for Structured Outputs
            (``client.messages.parse``); when None, plain
            ``client.messages.create`` is used.
        :return: dict with ``parsed`` (when ``output_format`` given),
            ``text``, ``usage`` (input/cache_creation/cache_read/output
            tokens), ``model``, ``stop_reason``, ``request_id``.
        :raises UserError: mapped from the SDK hierarchy, most-specific-first,
            so accountants see a plain-language action ("wait Ns and retry"
            vs "call IT") instead of a stack trace.
        """
        client = self._client()
        model = self._model()
        if max_tokens is None:
            max_tokens = ANTHROPIC_MAX_TOKENS

        try:
            if output_format is not None:
                try:
                    response = client.messages.parse(
                        model=model,
                        max_tokens=max_tokens,
                        system=system_blocks,
                        messages=messages,
                        output_format=output_format,
                    )
                    parsed = response.parsed_output
                except TypeError:
                    # Older SDK without messages.parse(): fall back to
                    # output_schema= and let pydantic validate afterwards.
                    _logger.info(
                        "invoice_agent: messages.parse() unavailable, falling "
                        "back to output_schema= (model %s)",
                        model,
                    )
                    response = client.messages.create(
                        model=model,
                        max_tokens=max_tokens,
                        system=system_blocks,
                        messages=messages,
                        output_schema=invoice_extraction_json_schema(),
                    )
                    parsed = output_format.model_validate_json(
                        response.content[0].text,
                    )
            else:
                response = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system_blocks,
                    messages=messages,
                )
                parsed = None
        except Exception as exc:
            raise self._map_sdk_error(exc) from exc

        if response.stop_reason == "max_tokens":
            # Never persist a truncated half-record silently: raise loudly so
            # the caller marks the record failed instead of 'extracted'.
            raise UserError(
                _(
                    "Claude stopped because it hit max_tokens during invoice "
                    "extraction â€” the record is incomplete. Increase "
                    "ANTHROPIC_MAX_TOKENS and retry.",
                ),
            )

        usage = response.usage
        usage_dict = {
            "input_tokens": getattr(usage, "input_tokens", None),
            "cache_creation_input_tokens": getattr(
                usage, "cache_creation_input_tokens", None,
            ),
            "cache_read_input_tokens": getattr(
                usage, "cache_read_input_tokens", None,
            ),
            "output_tokens": getattr(usage, "output_tokens", None),
        }
        _logger.info(
            "invoice_agent _call_claude: model=%s usage=%s stop=%s",
            model,
            usage_dict,
            response.stop_reason,
        )
        return {
            "parsed": parsed,
            "text": getattr(response.content[0], "text", None),
            "usage": usage_dict,
            "model": getattr(response, "model", model),
            "stop_reason": response.stop_reason,
            "request_id": getattr(response, "_request_id", None),
        }

    @api.model
    def _map_sdk_error(self, exc):
        """Map the SDK exception hierarchy to distinct Odoo UserErrors.

        Imported lazily so a stale image without ``anthropic`` still produces
        the generic message below instead of a NameError.

        Order matters â€” most specific first:
        1. NotFoundError      â€” 404: the model id is wrong/retired.
        2. RateLimitError     â€” 429: we hit the rate limit; honor Retry-After.
        3. APIStatusError     â€” any other HTTP status (4xx/5xx) from Claude.
        4. APIConnectionError â€” transport failure: network, DNS, TLS.
        """
        try:
            import anthropic
        except ImportError:
            return UserError(
                _("Claude call failed: %s", exc),
            )

        if isinstance(exc, anthropic.NotFoundError):
            return UserError(
                _(
                    "The Anthropic model '%s' was not found (HTTP 404). The "
                    "model may have been retired or the configured id is "
                    "wrong â€” contact IT to update the model setting.",
                    getattr(exc, "message", None),
                ),
            )
        if isinstance(exc, anthropic.RateLimitError):
            retry_after = extract_retry_after_seconds(exc)
            if retry_after:
                return UserError(
                    _(
                        "Anthropic is rate-limiting the extraction service. "
                        "Wait about %d seconds and try again.",
                        retry_after,
                    ),
                )
            return UserError(
                _(
                    "Anthropic is rate-limiting the extraction service. Try "
                    "again in a minute.",
                ),
            )
        if isinstance(exc, anthropic.APIStatusError):
            return UserError(
                _(
                    "The Anthropic API returned HTTP %s for the extraction "
                    "call. This is a server-side failure outside our "
                    "configuration â€” contact IT with the request id if it "
                    "persists.",
                    getattr(exc, "status_code", "unknown"),
                ),
            )
        if isinstance(exc, anthropic.APIConnectionError):
            return UserError(
                _(
                    "Could not reach the Anthropic API (network or connection "
                    "failure). Check your internet connection and try again.",
                ),
            )
        # Anything else (e.g. validation inside pydantic, SDK bugs) â€” keep
        # the original exception chain for the log, surface a clean message.
        _logger.exception("invoice_agent unexpected Claude error: %r", exc)
        return UserError(_("Claude call failed: %s", exc))

    # ------------------------------------------------------------------
    # Extract
    # ------------------------------------------------------------------
    @api.model
    def extract_invoice(self, text):
        """Run structured extraction against Claude and validate the output.

        :param text: the raw OCR / invoice text
        :return: dict with ``parsed`` (the schema-validated
                 ``InvoiceExtraction`` object), ``usage`` (input/output/
                 cache tokens), ``model`` and ``stop_reason``
        :raises UserError: mapped by :meth:`_call_claude`; a truncated
            response (``stop_reason == 'max_tokens'``) raises too.
        """
        self.ensure_one()
        if not text:
            raise UserError(_("No invoice text to extract."))

        # The cacheable system prefix (instructions + chart of accounts) is
        # frozen; only the invoice text varies, and it lives last in
        # messages so the prefix stays byte-identical across invoices.
        result = self._call_claude(
            system_blocks=self._extraction_system_blocks(),
            messages=[
                {
                    "role": "user",
                    "content": text,
                },
            ],
            output_format=InvoiceExtraction,
        )
        return result

    # ------------------------------------------------------------------
    # Usage ledger
    # ------------------------------------------------------------------
    @api.model
    def log_usage(self, move_id, usage, model=None):
        """Persist one extraction's token+cost ledger row.

        Called by the extraction pipeline after a successful call. Cost is
        computed by the model itself at Opus rates (see
        ``invoice.agent.usage``). Never raises â€” usage logging must not take
        down an otherwise-successful extraction.
        """
        try:
            self.env["invoice.agent.usage"].sudo().create(
                {
                    "move_id": move_id,
                    "model": model or self._model(),
                    "input_tokens": usage.get("input_tokens") or 0,
                    "cache_creation_input_tokens": usage.get(
                        "cache_creation_input_tokens", 0,
                    ) or 0,
                    "cache_read_input_tokens": usage.get(
                        "cache_read_input_tokens", 0,
                    ) or 0,
                    "output_tokens": usage.get("output_tokens") or 0,
                },
            )
        except Exception:
            _logger.exception(
                "invoice_agent failed to log usage for move_id=%s", move_id,
            )

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
        result = self._call_claude(
            system_blocks=system_prompt,
            messages=messages,
            max_tokens=1000,
        )
        return {
            "content": result["text"],
            "usage": {
                "input_tokens": result["usage"].get("input_tokens"),
                "output_tokens": result["usage"].get("output_tokens"),
            },
        }

    # ------------------------------------------------------------------
    # Raw payload serialization (for ai_extracted_json)
    # ------------------------------------------------------------------
    @api.model
    def extraction_to_dict(self, extraction):
        """Serialize a validated ``InvoiceExtraction`` to a plain dict.

        Decimal / date objects are not JSON-serializable by the ``json``
        module alone â€” this is the single place that knows how to render them.
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
