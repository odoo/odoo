"""Anthropic client — the only module that touches the Claude SDK.

Why ``AsyncAnthropic`` (the brief's core lesson): the sync
``anthropic.Anthropic`` blocks the calling thread for the whole HTTP
round-trip. Inside a FastAPI ``async def`` endpoint that blocks the event
loop and stalls every concurrent request in the same uvicorn process. With
``AsyncAnthropic`` the SDK uses ``httpx.AsyncClient``; the event loop stays
free while awaiting the network call — Odoo's "one worker, one request at a
time" problem does not exist here because a single async service can
concurrently await many Claude calls.

Prompt caching: the frozen instructions (``prompts/v3.md``) are the
cacheable system prefix; ``cache_control`` sits on the **last** block so the
whole prefix is cached. The volatile invoice text stays last in ``messages``.
The prefix must be >= 4096 tokens on ``claude-opus-4-8`` before reads
register — the service prompt is built to exceed that with the rules block.

Error contract (``app/errors.py``): every upstream failure surfaces as a
typed exception that the router maps to the OpenAPI ``ErrorEnvelope``.
"""

import logging
from datetime import UTC
from typing import Any

from anthropic import (
    APIConnectionError,
    APIStatusError,
    AsyncAnthropic,
    NotFoundError,
)
from anthropic.types import CacheControlEphemeralParam, Message, TextBlockParam

from .config import Settings, settings
from .errors import (
    ClaudeRateLimitError,
    ClaudeUpstreamError,
    ExtractionValidationError,
)
from .schemas import InvoiceExtraction, invoice_extraction_json_schema

_logger = logging.getLogger(__name__)

CACHE_CONTROL: CacheControlEphemeralParam = {"type": "ephemeral"}


def _system_blocks() -> list[TextBlockParam]:
    """Build the cacheable system prefix from prompts/v3.md.

    ``cache_control`` on the last block marks the whole prefix cacheable.
    The invoice text is never part of this prefix (it lives in ``messages``),
    so the prefix stays byte-identical across invoices and the cache hits.
    """
    from pathlib import Path

    prompt_path = Path(__file__).parent / "prompts" / "v3.md"
    instructions = prompt_path.read_text(encoding="utf-8")
    return [
        {"type": "text", "text": instructions},
        {
            "type": "text",
            "text": "Extraction rules above are authoritative. Return ONLY a "
            "valid JSON object matching the provided schema.",
            "cache_control": CACHE_CONTROL,
        },
    ]


def _usage_dict(message: Message) -> dict[str, Any]:
    usage = message.usage
    return {
        "input_tokens": getattr(usage, "input_tokens", None),
        "cache_creation_input_tokens": getattr(
            usage, "cache_creation_input_tokens", None,
        ),
        "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
    }


def _retry_after_seconds(exc: object) -> int | None:
    """Read Anthropic's Retry-After header (int seconds or HTTP-date)."""
    import email.utils
    from datetime import datetime

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
        delta = retry_at - datetime.now(UTC)
        return max(1, int(delta.total_seconds()))
    except (TypeError, ValueError):
        return None


def _map_upstream_error(exc: Exception) -> Exception:
    """Map the SDK exception hierarchy to service exceptions."""
    if isinstance(exc, NotFoundError):
        return ClaudeUpstreamError(
            "model-not-found",
            f"Anthropic model not found (HTTP 404): {exc}",
        )
    if isinstance(exc, APIStatusError) and exc.status_code == 429:
        return ClaudeRateLimitError(
            retry_after_seconds=_retry_after_seconds(exc) or 60,
            message=f"Anthropic rate limit (HTTP 429): {exc}",
        )
    if isinstance(exc, APIStatusError):
        return ClaudeUpstreamError(
            code=f"upstream-http-{exc.status_code}",
            message=f"Anthropic API returned HTTP {exc.status_code}",
        )
    if isinstance(exc, APIConnectionError):
        return ClaudeUpstreamError(
            code="upstream-connection",
            message="Could not reach the Anthropic API",
        )
    _logger.exception("unexpected Claude error: %r", exc)
    return ClaudeUpstreamError("upstream-unknown", str(exc))


class ClaudeService:
    """Structured-output extraction via AsyncAnthropic.messages.parse.

    Injectable into endpoints via ``Depends(get_claude_service)`` (see
    ``app/dependencies.py``). Tests replace this whole service with a fake.
    """

    def __init__(self, client: AsyncAnthropic | None = None, cfg: Settings = settings):
        self._client = client or AsyncAnthropic(
            api_key=cfg.anthropic_api_key,
            timeout=cfg.anthropic_timeout_seconds,
            max_retries=cfg.anthropic_max_retries,
        )
        self._cfg = cfg

    async def extract(self, text: str, effort: str = "normal") -> dict[str, Any]:
        """Extract structured invoice data from OCR text.

        :return: dict with ``parsed`` (validated ``InvoiceExtraction``),
            ``usage``, ``model``.
        :raises ClaudeRateLimitError / ClaudeUpstreamError /
            ExtractionValidationError.
        """
        # Never pass None to messages.parse(output_config=...): the SDK
        # merges {**output_config, "format": ...} and crashes on None.
        output_config: Any = {}
        if effort and effort != "normal":
            output_config = {"effort": effort}

        # ``message`` is typed as Any because the version-fallback path below
        # can bind either a ParsedMessage[InvoiceExtraction] (messages.parse)
        # or a plain Message (messages.create) — the SDK stubs type the two
        # differently. Both expose .usage/.model/.stop_reason/.content, and
        # "_parse_content" normalizes the fallback, so the ambiguity is
        # confined to this method.
        message: Any
        # Wrap OCR text in delimiters (OWASP LLM01 — prompt injection
        # mitigation). The system prompt in prompts/v3.md already instructs
        # Claude to ignore instructions inside scanned content; the
        # delimiters make the boundary explicit so the model can
        # distinguish system instructions from adversarial invoice text.
        isolated_text = (
            "<<<SCAN_CONTENT>>>\n" + (text or "No OCR text available")
            + "\n<<<END_SCAN_CONTENT>>>\n\n"
            "Extract structured invoice data from the scanned content above."
        )
        try:
            message = await self._client.messages.parse(
                model=self._cfg.anthropic_model,
                max_tokens=self._cfg.anthropic_max_tokens,
                system=_system_blocks(),
                messages=[{"role": "user", "content": isolated_text}],
                output_format=InvoiceExtraction,
                output_config=output_config,
            )
            parsed: InvoiceExtraction = message.parsed_output
        except TypeError:
            # Older SDK without messages.parse(): fall back to JSON schema
            # in output_config and validate with pydantic. The ``create``
            # call is deliberately version-agnostic (the json_schema dict is
            # accepted at runtime), so the strict OutputConfigParam stub
            # mismatch is silenced.
            _logger.info("messages.parse unavailable; using json_schema path")
            message = await self._client.messages.create(
                model=self._cfg.anthropic_model,
                max_tokens=self._cfg.anthropic_max_tokens,
                system=_system_blocks(),
                messages=[{"role": "user", "content": isolated_text}],
                output_config={
                    "format": {
                        "type": "json_schema",
                        "schema": invoice_extraction_json_schema(),
                    }
                },
            )
            parsed = self._parse_content(message)
        except NotFoundError as exc:
            raise _map_upstream_error(exc) from exc
        except APIStatusError as exc:
            raise _map_upstream_error(exc) from exc
        except APIConnectionError as exc:
            raise _map_upstream_error(exc) from exc

        if message.stop_reason == "max_tokens":
            raise ExtractionValidationError(
                "Claude stopped at max_tokens — response truncated",
            )
        return {
            "parsed": parsed,
            "usage": _usage_dict(message),
            "model": getattr(message, "model", self._cfg.anthropic_model),
        }

    def _parse_content(self, message: Message) -> InvoiceExtraction:
        content = "".join(
            getattr(block, "text", "") for block in message.content
        )
        try:
            return InvoiceExtraction.model_validate_json(content)
        except Exception as exc:
            raise ExtractionValidationError(
                f"Claude returned content that fails schema validation: {exc}",
            ) from exc


def get_claude_service() -> ClaudeService:
    """FastAPI ``Depends()`` factory for the Anthropic-backed service."""
    return ClaudeService()
