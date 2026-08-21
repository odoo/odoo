"""LLM service — HTTP client for the standalone ``invoice-ai`` FastAPI service.

The week's milestone replaced the in-process Anthropic SDK call with an HTTP
call to the ``invoice-ai`` service (ADR-003): Odoo never blocks an HTTP
worker on a 5-20 s LLM round-trip anymore — the service owns OCR + the Claude
call, and this module is a thin, hardened HTTP client.

Service contract:

* ``extract_invoice(text, effort="normal")`` mints a **60-second HS256 JWT**
  (``iss``/``aud``/``sub``/``iat``/``exp``) and
  ``requests.post(base_url + '/v1/extract', files=..., headers=...,
  timeout=90)``. The base URL and the shared JWT secret are read from
  ``ir.config_parameter`` (``invoice_agent.llm_service_url`` /
  ``invoice_agent.jwt_secret``) — never from source. The JSON response is
  re-validated through the addon's own ``InvoiceExtraction`` pydantic schema
  and returned in the same ``{"parsed", "usage", "model"}`` dict shape the
  callers already consume, so ``account_move.py`` is unchanged.
* Failure mapping (clean Odoo outcomes, never a traceback):
    - ``requests.Timeout``                -> one retry, then ``UserError``
    - HTTP 401 (bad/expired token or
      wrong secret on the service side)  -> ``UserError`` "config error"
    - HTTP 503 (upstream AI unavailable)  -> raises ``AIServiceUnavailable``;
      the extraction call sites set ``ocr_state='pending'`` so the ir.cron
      worker retries later instead of marking the bill permanently failed.
    - HTTP 413/415/400/422                -> ``UserError`` with the service's
      error message.
* Circuit breaker: a module-level failure counter ``_circuit`` trips open
  after ``CIRCUIT_FAILURE_THRESHOLD`` consecutive failures and refuses new
  calls for ``CIRCUIT_RESET_SECONDS`` — a dead service is never hammered.
  A success resets the counter. (Per-process by design: the cron worker and
  the HTTP workers each bound their own blast radius.)
* ``score_extraction`` / ``confidence_threshold`` / ``log_usage`` /
  ``extraction_to_dict`` are unchanged — the confidence blend, routing
  threshold and usage ledger are deterministic Odoo-side logic that has
  nothing to do with *where* the Claude call runs.

Config parameters (read via ``ir.config_parameter``, set in Settings →
Invoice Agent):

* ``invoice_agent.llm_service_url`` — e.g. ``http://invoice-ai:8000``
  (the compose service name on the internal bridge network).
* ``invoice_agent.jwt_secret`` — the shared HS256 secret, must equal the
  service's ``INVOICE_AI_JWT_SECRET``.
"""

import json
import logging
import time
from datetime import UTC

import requests

from odoo import _, api, models
from odoo.exceptions import UserError

from .confidence import apply_rescues, combined_confidence
from .invoice_extraction import (
    _PYDANTIC_AVAILABLE,
    InvoiceExtraction,
)

_logger = logging.getLogger(__name__)

# ir.config_parameter keys — the two settings the service-to-service call
# needs. Both are secrets/config, never addon source.
LLM_SERVICE_URL_PARAM = "invoice_agent.llm_service_url"
JWT_SECRET_PARAM = "invoice_agent.jwt_secret"
EMBED_PATH = "/v1/embed"
# voyage-3 embedding dimension — must match the service (app/embeddings.py)
# and the vector(1024) column in invoice_agent_vendor_doc.
EMBED_DIMENSIONS = 1024
EMBED_TIMEOUT_SECONDS = 60

# The audience must match the service's INVOICE_AI_JWT_AUDIENCE
# (default "invoice-ai"). A token minted with the right secret but the wrong
# audience dies on the service side with 401.
JWT_AUDIENCE = "invoice-ai"
JWT_TTL_SECONDS = 60

# requests.post(timeout=...) for one /v1/extract round trip. The service
# itself allows 90 s for the Claude call; 90 s here covers that plus the
# network hop, and 60 s of JWT validity is plenty inside one attempt.
EXTRACT_TIMEOUT_SECONDS = 90

# requests.Timeout is retried ONCE before surfacing a UserError. The service
# already retries idempotent 429/5xx internally (2 retries); a timeout here
# is a network-level drop that a single second attempt usually survives.
TIMEOUT_RETRIES = 1

# ---------------------------------------------------------------------------
# Claude Opus 4 pricing (USD per million tokens) — used by models/usage.py
# to compute each extraction's ledger cost. Cache writes and reads are
# billed at 25% / 10% of the input price respectively.
# ---------------------------------------------------------------------------
OPUS_PRICE_PER_MT_INPUT = 15.00
OPUS_PRICE_PER_MT_CACHE_WRITE = 3.75  # 25% of input
OPUS_PRICE_PER_MT_CACHE_READ = 1.50  # 10% of input
OPUS_PRICE_PER_MT_OUTPUT = 75.00

# ---------------------------------------------------------------------------
# Circuit breaker (per-process).
# ---------------------------------------------------------------------------
CIRCUIT_FAILURE_THRESHOLD = 5
CIRCUIT_RESET_SECONDS = 300

_circuit = {
    "consecutive_failures": 0,
    "open_until": 0.0,  # monotonic() timestamp; 0 = closed
}

CONFIDENCE_THRESHOLD_PARAM = "invoice_agent.confidence_threshold"
DEFAULT_CONFIDENCE_THRESHOLD = 0.80

# --- Tiered confidence routing (v0.11 — two thresholds, three bins) ------
AUTO_FILL_THRESHOLD_PARAM = "invoice_agent.auto_fill_threshold"
DEFAULT_AUTO_FILL_THRESHOLD = 0.90
REVIEW_THRESHOLD_PARAM = "invoice_agent.review_threshold"
DEFAULT_REVIEW_THRESHOLD = 0.60

# --- RAG kill switch -------------------------------------------------------
RAG_ENABLED_PARAM = "invoice_agent.rag_enabled"
DEFAULT_RAG_ENABLED = True


def _circuit_open() -> bool:
    """True when the breaker is tripped and the reset window hasn't elapsed."""
    if _circuit["consecutive_failures"] < CIRCUIT_FAILURE_THRESHOLD:
        return False
    if time.monotonic() >= _circuit["open_until"]:
        # Reset window elapsed — close the circuit and let one probe through
        # (half-open: a success re-arms, a failure re-opens immediately).
        _circuit["consecutive_failures"] = 0
        return False
    return True


def _circuit_record_success():
    _circuit["consecutive_failures"] = 0
    _circuit["open_until"] = 0.0


def _circuit_record_failure():
    _circuit["consecutive_failures"] += 1
    if _circuit["consecutive_failures"] >= CIRCUIT_FAILURE_THRESHOLD:
        _circuit["open_until"] = time.monotonic() + CIRCUIT_RESET_SECONDS
        _logger.error(
            "invoice_agent: circuit breaker OPEN — %d consecutive AI service "
            "failures, refusing calls for %.0fs",
            _circuit["consecutive_failures"],
            CIRCUIT_RESET_SECONDS,
        )


class AIServiceUnavailable(Exception):
    """Raised on HTTP 503 / upstream-AI failure.

    Unlike a plain ``UserError``, callers catch this specific type to route
    the record into ``ocr_state='pending'`` for the cron retry instead of
    marking it permanently failed.
    """


def mint_jwt(
    secret,
    audience=JWT_AUDIENCE,
    ttl_seconds=JWT_TTL_SECONDS,
    subject="invoice.llm.service",
    issuer="odoo.invoice-agent",
):
    """Mint the JWT Odoo sends to ``invoice-ai`` (HS256, 60 s, no refresh).

    Claims follow the brief: ``iss``, ``aud``, ``sub``, ``iat``, ``exp``.
    Short expiry is deliberate — the token is minted immediately before the
    request and only needs to outlive a 90 s timeout, so a leaked token is
    worthless in minutes. No refresh token: service-to-service calls just
    mint a fresh one.
    """
    from datetime import datetime, timedelta

    import jwt

    now = datetime.now(UTC)
    return jwt.encode(
        {
            "iss": issuer,
            "aud": audience,
            "sub": subject,
            "iat": now,
            "exp": now + timedelta(seconds=ttl_seconds),
        },
        secret,
        algorithm="HS256",
    )


def extract_retry_after_seconds(body):
    """Read ``retry_after_seconds`` from the service's ErrorEnvelope.

    Returns an int >= 1 when present, else ``None``.
    """
    envelope = body.get("error") if isinstance(body, dict) else None
    if not envelope:
        return None
    value = envelope.get("retry_after_seconds")
    if value is None:
        return None
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return None


class InvoiceLlmService(models.AbstractModel):
    _name = "invoice.llm.service"
    _description = "HTTP client for the invoice-ai extraction service"

    # ------------------------------------------------------------------
    # Config resolution (ir.config_parameter — never source)
    # ------------------------------------------------------------------
    @api.model
    def _service_url(self):
        """Base URL of the invoice-ai service, e.g. http://invoice-ai:8000."""
        url = self.env["ir.config_parameter"].sudo().get_param(LLM_SERVICE_URL_PARAM)
        if not url:
            raise UserError(
                _(
                    "The AI service URL is not configured. Set it in Settings → "
                    "Invoice Agent → LLM Service URL (e.g. "
                    "http://invoice-ai:8000).",
                ),
            )
        return url.rstrip("/")

    @api.model
    def _jwt_secret(self):
        """The shared HS256 secret (must match the service's JWT_SECRET)."""
        secret = self.env["ir.config_parameter"].sudo().get_param(JWT_SECRET_PARAM)
        if not secret:
            raise UserError(
                _(
                    "The AI service JWT secret is not configured. Set it in "
                    "Settings → Invoice Agent → JWT Secret — it must equal the "
                    "service's INVOICE_AI_JWT_SECRET.",
                ),
            )
        return secret

    @api.model
    def confidence_threshold(self):
        """Resolve the global auto-approval threshold (0..1)."""
        raw = (
            self.env["ir.config_parameter"].sudo().get_param(CONFIDENCE_THRESHOLD_PARAM)
        )
        if not raw:
            return None
        try:
            value = float(raw)
        except (TypeError, ValueError):
            _logger.warning(
                "invoice_agent: invalid confidence_threshold %r — ignoring",
                raw,
            )
            return None
        return max(0.0, min(1.0, value))

    # ------------------------------------------------------------------
    # Tiered confidence routing (v0.11 — three bins)
    # ------------------------------------------------------------------
    @api.model
    def auto_fill_threshold(self):
        """Resolve the auto-fill threshold (above this: pre-fill + ready).

        ``ir.config_parameter`` → 0.90 default.
        """
        raw = (
            self.env["ir.config_parameter"].sudo().get_param(AUTO_FILL_THRESHOLD_PARAM)
        )
        if not raw:
            return DEFAULT_AUTO_FILL_THRESHOLD
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return DEFAULT_AUTO_FILL_THRESHOLD
        return max(0.0, min(1.0, value))

    @api.model
    def review_threshold(self):
        """Resolve the review threshold (below this: needs_human).

        Between review_threshold and auto_fill_threshold → needs_review
        kanban column.  Below review_threshold → needs_human flag.

        ``ir.config_parameter`` → 0.60 default.
        """
        raw = self.env["ir.config_parameter"].sudo().get_param(REVIEW_THRESHOLD_PARAM)
        if not raw:
            return DEFAULT_REVIEW_THRESHOLD
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return DEFAULT_REVIEW_THRESHOLD
        return max(0.0, min(1.0, value))

    @api.model
    def rag_enabled(self):
        """Check whether RAG validation is enabled (kill switch).

        When False, the consumer skips retrieve + validate and publishes
        extraction results without the validation envelope — reverting to
        v0.9 extraction-only behaviour.

        ``ir.config_parameter`` → True (RAG enabled) by default.
        """
        raw = self.env["ir.config_parameter"].sudo().get_param(RAG_ENABLED_PARAM)
        if raw is None:
            return DEFAULT_RAG_ENABLED
        return raw.lower() in ("true", "1", "yes")

    # ------------------------------------------------------------------
    # HTTP call to invoice-ai
    # ------------------------------------------------------------------
    @api.model
    def extract_invoice(self, text, effort="normal"):
        """Extract structured invoice data via the invoice-ai HTTP service.

        :param text: raw OCR / invoice text.
        :param effort: ``"normal"`` (default) or ``"high"`` — passed to the
            service as the multipart ``effort`` form field.
        :return: dict with ``parsed`` (schema-validated
                 ``InvoiceExtraction``), ``usage``, ``model`` — the exact
                 shape the callers already consume.
        :raises UserError: config errors (401, missing settings), timeout
            (retried once), 4xx from the service.
        :raises AIServiceUnavailable: HTTP 503 — callers route the record to
            ``ocr_state='pending'`` for cron retry.
        """
        if not text:
            raise UserError(_("No invoice text to extract."))
        if _circuit_open():
            _logger.warning(
                "invoice_agent: refusing extraction — circuit breaker open",
            )
            msg = (
                "The AI service is unavailable (circuit breaker open). "
                "The bill was queued for automatic retry."
            )
            raise AIServiceUnavailable(
                msg,
            )
        if not _PYDANTIC_AVAILABLE:
            raise UserError(_("pydantic is not installed in the running image."))

        url = self._service_url()
        secret = self._jwt_secret()
        token = mint_jwt(secret)
        headers = {"Authorization": f"Bearer {token}"}

        last_timeout = None
        for attempt in range(TIMEOUT_RETRIES + 1):
            try:
                response = requests.post(
                    url + "/v1/extract",
                    files={"text": (None, text)},
                    data={"effort": effort},
                    headers=headers,
                    timeout=EXTRACT_TIMEOUT_SECONDS,
                )
                break
            except requests.Timeout as exc:
                last_timeout = exc
                _logger.warning(
                    "invoice_agent: /v1/extract timeout (attempt %d/%d)",
                    attempt + 1,
                    TIMEOUT_RETRIES + 1,
                )
                if attempt >= TIMEOUT_RETRIES:
                    _circuit_record_failure()
                    raise UserError(
                        _(
                            "The AI extraction service timed out after %d "
                            "attempts. Check that invoice-ai is reachable at "
                            "'%s' and try again.",
                            TIMEOUT_RETRIES + 1,
                            url,
                        ),
                    ) from exc
        else:
            # The loop fell through without a response (retries exhausted).
            # Cannot happen with the raise above, kept for mypy.
            assert last_timeout is not None  # pragma: no cover
            raise UserError(_("The AI extraction service is unreachable."))

        return self._parse_extract_response(response, url)

    def _parse_extract_response(self, response, url):
        """Turn the service's HTTP response into the caller-facing dict."""
        try:
            body = response.json()
        except ValueError:
            body = {}

        if response.status_code == 503:
            retry_after = extract_retry_after_seconds(body)
            hint = (
                _(" Retry after about %d seconds.") % retry_after if retry_after else ""
            )
            _logger.warning(
                "invoice_agent: AI service 503 at %s — queued for retry%s",
                url,
                hint,
            )
            _circuit_record_failure()
            raise AIServiceUnavailable(
                _("The AI service is temporarily unavailable.%s", hint),
            )

        if response.status_code == 401:
            # 401 from the service means OUR token was rejected — either the
            # shared secret drifted between the two sides or the clock skew
            # exceeded leeway. Either way it is an Odoo-side config error, not
            # a transient failure: raise immediately, never retry.
            _logger.error(
                "invoice_agent: AI service rejected our JWT (401) at %s — "
                "check invoice_agent.jwt_secret vs INVOICE_AI_JWT_SECRET",
                url,
            )
            _circuit_record_failure()
            raise UserError(
                _(
                    "The AI service rejected the authentication token (HTTP "
                    "401). The JWT secret configured in Settings → Invoice "
                    "Agent does not match the service's INVOICE_AI_JWT_SECRET, "
                    "or the clocks are too far apart.",
                ),
            )

        if response.status_code >= 500:
            message = (
                body.get("error", {}).get("message") if isinstance(body, dict) else None
            )
            _logger.error(
                "invoice_agent: AI service HTTP %s at %s — %s",
                response.status_code,
                url,
                message or body,
            )
            _circuit_record_failure()
            raise AIServiceUnavailable(
                _(
                    "The AI service returned HTTP %s. The bill was queued for "
                    "automatic retry.",
                    response.status_code,
                ),
            )

        if response.status_code != 200:
            # 400/413/415/422 — a request problem, surfaced as a UserError.
            message = (
                body.get("error", {}).get("message") if isinstance(body, dict) else None
            )
            code = body.get("error", {}).get("code") if isinstance(body, dict) else None
            _logger.warning(
                "invoice_agent: AI service rejected request (HTTP %s, code %s): %s",
                response.status_code,
                code,
                message,
            )
            raise UserError(
                _(
                    "The AI service rejected the extraction request (HTTP %s, "
                    "code %s): %s",
                    response.status_code,
                    code or "unknown",
                    message or "no error detail",
                ),
            )

        # 200 — re-validate through the addon's own schema, then re-arm the
        # circuit breaker (a success clears the consecutive-failure counter).
        try:
            extraction = InvoiceExtraction.model_validate(
                body.get("extraction") or body,
            )
            _circuit_record_success()
        except Exception as exc:
            _logger.error(
                "invoice_agent: response from %s failed schema validation: %s",
                url,
                exc,
            )
            raise UserError(
                _(
                    "The AI service returned data that does not match the "
                    "extraction schema — the two sides have drifted. Contact IT.",
                ),
            ) from exc

        return {
            "parsed": extraction,
            "usage": body.get("usage") or {},
            "model": body.get("model") or "invoice-ai",
        }

    # ------------------------------------------------------------------
    # Embeddings (v0.10 — voyage-3 via the service)
    # ------------------------------------------------------------------
    @api.model
    def embed_texts(self, texts):
        """Embed RAG documents via the invoice-ai ``/v1/embed`` endpoint.

        :param texts: list of raw document strings (vendor-doc RAG content).
        :return: list of 1024-dim float vectors aligned with ``texts``, or
            ``None`` when the service is transiently unavailable — the
            caller keeps its rows ``ai_indexed=False`` and the backfill
            cron retries the batch later.
        :raises UserError: config / 401 / 4xx / dimension-drift problems
            (these are never fixed by retrying).
        """
        if not texts:
            return []
        url = self._service_url()
        secret = self._jwt_secret()
        token = mint_jwt(secret)
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = requests.post(
                url + EMBED_PATH,
                json={"texts": list(texts)},
                headers=headers,
                timeout=EMBED_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            _logger.warning(
                "invoice_agent: /v1/embed unreachable at %s — %s",
                url,
                exc,
            )
            return None
        try:
            body = response.json()
        except ValueError:
            body = {}
        if response.status_code == 503:
            _logger.warning(
                "invoice_agent: /v1/embed 503 at %s — embed deferred",
                url,
            )
            return None
        if response.status_code == 401:
            _logger.error(
                "invoice_agent: /v1/embed rejected our JWT (401) at %s",
                url,
            )
            raise UserError(
                _(
                    "The AI service rejected the embedding token (HTTP 401). "
                    "The JWT secret is out of sync with INVOICE_AI_JWT_SECRET.",
                ),
            )
        if response.status_code != 200:
            message = (
                body.get("error", {}).get("message") if isinstance(body, dict) else None
            )
            raise UserError(
                _(
                    "The AI service rejected the embed request (HTTP %s): %s",
                    response.status_code,
                    message or "no error detail",
                ),
            )
        vectors = body.get("vectors") or []
        if len(vectors) != len(texts):
            raise UserError(
                _(
                    "The AI service returned %(got)s vectors for %(want)s "
                    "texts — the two sides have drifted."
                )
                % {"got": len(vectors), "want": len(texts)},
            )
        for vector in vectors:
            dimension = len(vector) if isinstance(vector, list) else 0
            if dimension != EMBED_DIMENSIONS:
                raise UserError(
                    _(
                        "The AI service returned a %(dim)s-dim embedding — "
                        "expected %(want)s (voyage-3)."
                    )
                    % {"dim": dimension, "want": EMBED_DIMENSIONS},
                )
        return vectors

    # ------------------------------------------------------------------
    # Calibrated confidence (unchanged — deterministic Odoo-side logic)
    # ------------------------------------------------------------------
    @api.model
    def score_extraction(
        self, payload, ocr_text=None, ocr_confidence=None, checks=None
    ):
        """Compute the calibrated confidence score for an extraction payload.

        :return: ``(score, details)`` — see ``models/confidence.py``.
        """
        payload = dict(payload or {})
        checks = list(checks or [])
        checks += apply_rescues(payload, ocr_text)
        score, details = combined_confidence(
            payload,
            ocr_text=ocr_text,
            ocr_confidence=ocr_confidence,
            checks=checks,
        )
        details["rescued_payload"] = payload
        return score, details

    # ------------------------------------------------------------------
    # Usage ledger (unchanged)
    # ------------------------------------------------------------------
    @api.model
    def log_usage(self, move_id, usage, model=None):
        """Persist one extraction's token+cost ledger row. Never raises."""
        try:
            self.env["invoice.agent.usage"].sudo().create(
                {
                    "move_id": move_id,
                    "model": model or "invoice-ai",
                    "input_tokens": usage.get("input_tokens") or 0,
                    "cache_creation_input_tokens": usage.get(
                        "cache_creation_input_tokens",
                        0,
                    )
                    or 0,
                    "cache_read_input_tokens": usage.get(
                        "cache_read_input_tokens",
                        0,
                    )
                    or 0,
                    "output_tokens": usage.get("output_tokens") or 0,
                },
            )
        except Exception:
            _logger.exception(
                "invoice_agent failed to log usage for move_id=%s",
                move_id,
            )

    # ------------------------------------------------------------------
    # Raw payload serialization (unchanged)
    # ------------------------------------------------------------------
    @api.model
    def extraction_to_dict(self, extraction):
        """Serialize a validated ``InvoiceExtraction`` to a plain dict."""
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

    # ------------------------------------------------------------------
    # Compatibility wrapper (legacy suite / scratch scripts)
    # ------------------------------------------------------------------
    @api.model
    def call_claude(self, system_prompt, messages):
        """Legacy API kept so early tests keep running.

        The in-process Anthropic client is gone — there is no ``system_prompt``
        concept on the service boundary (the prompt lives in the service). The
        wrapper extracts the user text from the messages and delegates to
        :meth:`extract_invoice`, returning the legacy ``{"content", "usage"}``
        shape (plain JSON string in ``content``).
        """
        user_text = ""
        for message in messages or []:
            if isinstance(message, dict) and message.get("role") == "user":
                user_text = message.get("content") or ""
        result = self.extract_invoice(user_text)
        payload = self.extraction_to_dict(result["parsed"])
        return {
            "content": json.dumps(payload),
            "usage": {
                "input_tokens": result["usage"].get("input_tokens"),
                "output_tokens": result["usage"].get("output_tokens"),
            },
        }

    @api.model
    def reset_circuit_breaker_for_tests(self):
        """Test-only hook: close a tripped circuit breaker."""
        _circuit["consecutive_failures"] = 0
        _circuit["open_until"] = 0.0
