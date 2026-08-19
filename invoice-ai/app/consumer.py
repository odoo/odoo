"""Async worker — consumes ``invoice.extract`` jobs and publishes results.

Run with ``python -m app.consumer`` (the compose ``worker`` service command).
Flow per job (QoS prefetch=1, manual ack):

1. Connect robustly (``aio_pika.connect_robust``) and declare the full
   topology (``app/amqp.py``) — re-declared on every reconnect so a broker
   reset heals itself.
2. Consume one ``extract.request`` message. Body contract
   (docs/queue-contract.md): ``{"move_id", "attachment_id", "attempt",
   "job_uuid", "ocr_text"}``.
3. Publish ``extract.started`` on the ``invoice.agent`` topic exchange ->
   ``invoice.result`` so the Odoo UI flips to *extracting* live.
4. Run Claude extraction (``ClaudeService.extract`` — AsyncAnthropic, never
   a blocking SDK call on the loop).
5. Publish the JWT-signed result (``app/result_signing.py``) on
   ``invoice.agent``/``extract.done`` -> ``invoice.result``, then ack the
   original.

Failure routing (v0.9 — retry ladder + dead-letter queue, see app/retry.py):

* ``ClaudeRateLimitError`` / ``ClaudeUpstreamError`` (429, 5xx, connection):
  publish on the DLX exchange to the retry tier selected by the attempt
  counter (``retry.5s`` -> ``retry.30s`` -> ``retry.5m``), then ack the
  original. The tier's ``x-message-ttl`` is the backoff; expiry re-publishes
  to ``invoice.agent``/``extract.request``. Exhausting the ladder
  dead-letters instead.
* ``BadRequestError`` / ``ExtractionValidationError`` / malformed body:
  publish on the DLX to ``extract.dead`` AND a signed ``status:"failed"``
  result on the topic exchange, then ack the original. The dead queue owns
  the message; the signed failure lets the Odoo result consumer mark the
  originating outbox job dead and flag the move. Retrying never fixes a bad
  schema — these must never burn another Anthropic call.
* Unknown failure without an attempt counter: discard (ack, no republish).
* ``x-delivery-limit: 3`` on the queue is the safety net: a worker crash
  mid-job (unacked) redelivers at most 3 times before the broker itself
  dead-letters. A poison PDF can never loop forever.

``connect_robust`` reattaches after broker restarts with built-in retry and
redeclares the topology on each reconnect, so the worker survives RabbitMQ
outages mid-batch.

Why publish on the named exchanges and never the default exchange: the
default exchange routes only by *exact queue name*. ``extract.done`` is a
routing key on the ``invoice.agent`` topic exchange bound by the
``invoice.result`` queue — publishing it on the default exchange would
silently drop the result.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractIncomingMessage

from .amqp import (
    DLX_EXCHANGE,
    EXCHANGE_NAME,
    QUEUE_EXTRACT,
    ROUTING_KEY_DONE,
    ROUTING_KEY_REQUEST,
    ROUTING_KEY_STARTED,
    declare_topology,
)
from .claude import ClaudeService
from .errors import BadRequestError, ClaudeRateLimitError, ClaudeUpstreamError
from .llm_cache import cache_get, cache_set
from .result_signing import sign_result
from .retrieve import retrieve_vendor_context
from .retry import DEAD_ROUTING_KEY, attempt_from_body, classify_failure
from .metrics import (
    CLAUDE_API_DURATION,
    RABBITMQ_QUEUE_DEPTH,
    WORKER_JOB_DURATION,
    WORKER_JOBS_TOTAL,
    Timer,
    record_claude_tokens,
)
from .schemas import InvoiceExtraction
from .validate import validate_extraction

_logger = logging.getLogger(__name__)

PREFETCH_COUNT = 1


class WorkerError(Exception):
    """Raised when a job cannot be processed at all (malformed body)."""


def _parse_body(message: AbstractIncomingMessage) -> dict:
    """Decode + validate the job body.

    :raises WorkerError: invalid JSON or a non-object body — the caller
        treats this as a poison message.
    """
    try:
        payload = json.loads(message.body or b"{}")
    except (TypeError, ValueError) as exc:
        raise WorkerError(f"invalid JSON body: {exc}") from exc
    if not isinstance(payload, dict):
        raise WorkerError(f"body is not a JSON object: {type(payload).__name__}")
    return payload


class InvoiceConsumer:
    """aio-pika consumer for the ``invoice.extract`` queue.

    Owns one robust connection + channel. Injectable ``claude`` and
    ``sign`` seams so tests can run the full routing logic on a fake broker
    (aio-pika's in-memory ``connect``) without touching Anthropic.
    """

    def __init__(
        self,
        claude: ClaudeService | None = None,
        sign: Callable[[dict[str, Any]], str] = sign_result,
    ):
        self._claude = claude or ClaudeService()
        self._sign = sign

    async def run(self, amqp_url: str) -> None:
        """Connect robustly and consume until cancelled."""
        connection = await aio_pika.connect_robust(amqp_url)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=PREFETCH_COUNT)

        # (Re)declare the full topology on every connect — see amqp.py.
        await declare_topology(channel)

        queue = await channel.declare_queue(QUEUE_EXTRACT, durable=True)
        await queue.bind(EXCHANGE_NAME, routing_key=ROUTING_KEY_REQUEST)

        topic_exchange = await channel.get_exchange(EXCHANGE_NAME)
        dlx = await channel.get_exchange(DLX_EXCHANGE)

        _logger.info(
            "invoice-ai worker: consuming %s (prefetch=%d)",
            QUEUE_EXTRACT,
            PREFETCH_COUNT,
        )
        try:
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    await self._handle_message(
                        channel,
                        message,
                        topic_exchange,
                        dlx,
                    )
        finally:
            await connection.close()
            _logger.info("invoice-ai worker: connection closed")

    async def _handle_message(
        self,
        channel: AbstractChannel,
        message: AbstractIncomingMessage,
        topic_exchange,
        dlx,
    ) -> None:
        async with message.process(requeue=False):
            try:
                body = _parse_body(message)
            except WorkerError as exc:
                await self._dead_letter(dlx, message, exc, topic_exchange)
                return

            attempt = attempt_from_body(body)
            job_uuid = body.get("job_uuid") or ""
            move_id = body.get("move_id")
            ocr_text = body.get("ocr_text") or ""

            # Track overall job duration from consume to result publish
            job_start = __import__("time").monotonic()

            if not job_uuid or not move_id:
                await self._dead_letter(
                    dlx,
                    message,
                    WorkerError("job body missing job_uuid/move_id"),
                    topic_exchange,
                )
                return

            try:
                await self._publish_started(topic_exchange, job_uuid, move_id)

                # --- LLM cache lookup ---
                # Check Redis for a cached extraction before calling Claude.
                # On hit, skip the API call entirely (saves tokens + latency).
                cached = cache_get(ocr_text, model=self._claude._cfg.anthropic_model)
                if cached and "result" in cached:
                    result = cached["result"]
                    _logger.info(
                        "invoice-ai worker: cache hit for move_id=%s",
                        move_id,
                    )
                else:
                    # Track Claude API latency in the worker
                    model_name = self._claude._cfg.anthropic_model
                    with Timer(CLAUDE_API_DURATION, model=model_name):
                        result = await self._claude.extract(text=ocr_text)
                    # Record token consumption
                    record_claude_tokens(
                        model=result["model"],
                        usage=result["usage"],
                    )
                    # Store in cache for future requests with same OCR text
                    try:
                        cache_set(
                            ocr_text,
                            result,
                            model=result.get("model", ""),
                        )
                    except Exception:
                        _logger.exception(
                            "invoice-ai worker: failed to cache result for "
                            "move_id=%s",
                            move_id,
                        )
            except (ClaudeRateLimitError, ClaudeUpstreamError, BadRequestError) as exc:
                decision = classify_failure(exc, attempt)
                await self._route_failure(dlx, message, decision, topic_exchange)
                return
            except Exception as exc:
                # Unknown/validation errors — be conservative, dead-letter.
                decision = classify_failure(exc, attempt)
                await self._route_failure(dlx, message, decision, topic_exchange)
                return

            # --- Phase 2: RAG validation (retrieve + validate) ---
            # Best-effort: if retrieval or validation fails, the extraction
            # result is still published — the Odoo side can surface it
            # without the validation envelope.
            #
            # The ``rag_enabled`` flag is a kill switch stored as
            # ``ir.config_parameter``. When False, the worker skips
            # retrieval + validation entirely, reverting to v0.9
            # extraction-only behaviour.
            validation_verdict = None
            validation_usage = None
            rag_enabled = body.get("rag_enabled", True)
            try:
                partner_id = body.get("partner_id")
                if partner_id and rag_enabled:
                    extraction: InvoiceExtraction = result["parsed"]
                    # Retrieve vendor context (hybrid vector + ref + VAT)
                    vendor_context = await retrieve_vendor_context(
                        partner_id=int(partner_id),
                        ocr_text=ocr_text,
                        extracted_ref=body.get("ref") or "",
                        extracted_vat=extraction.vendor_vat or "",
                        extracted_vendor_name=extraction.vendor_name or "",
                    )
                    # Validate extraction against vendor history
                    val_result = await validate_extraction(
                        extraction=extraction,
                        vendor_context=vendor_context,
                        ocr_text=ocr_text,
                    )
                    validation_verdict = val_result["verdict"].model_dump(
                        mode="json",
                    )
                    validation_usage = val_result["usage"]
                    _logger.info(
                        "invoice-ai worker: validation done for move_id=%s "
                        "account=%s confidence=%.2f cache_read=%s",
                        move_id,
                        validation_verdict.get("account_id"),
                        validation_verdict.get("account_confidence", 0),
                        validation_usage.get("cache_read_input_tokens")
                        if validation_usage
                        else None,
                    )
            except Exception:
                _logger.exception(
                    "invoice-ai worker: RAG validation failed for "
                    "move_id=%s — extraction result stands without validation",
                    move_id,
                )

            payload = {
                "job_uuid": job_uuid,
                "move_id": move_id,
                "status": "done",
                "parsed_output": result["parsed"].model_dump(mode="json"),
                "usage": result["usage"],
                "model": result["model"],
                "attempt": attempt or 1,
            }
            # Attach validation envelope when available
            if validation_verdict is not None:
                payload["validation"] = validation_verdict
                payload["validation_usage"] = validation_usage
            await self._publish_result(topic_exchange, payload)

            # Record successful job metrics
            job_elapsed = __import__("time").monotonic() - job_start
            WORKER_JOBS_TOTAL.labels(status="done").inc()
            WORKER_JOB_DURATION.observe(job_elapsed)
            _logger.info(
                "invoice-ai worker: job %s move_id=%s done model=%s "
                "validation=%s duration=%.1fs",
                job_uuid,
                move_id,
                result["model"],
                "yes" if validation_verdict else "no",
                job_elapsed,
            )

    async def _publish_started(self, topic_exchange, job_uuid: str, move_id: int) -> None:
        """Publish ``extract.started`` on the topic exchange (live UI state)."""
        await topic_exchange.publish(
            aio_pika.Message(
                body=json.dumps(
                    {
                        "job_uuid": job_uuid,
                        "move_id": int(move_id),
                        "status": "extracting",
                    },
                ).encode("utf-8"),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=ROUTING_KEY_STARTED,
        )

    async def _publish_result(self, topic_exchange, payload: dict) -> None:
        """Publish the JWT-signed ``extract.done`` result on the topic exchange."""
        token = self._sign(payload)
        await topic_exchange.publish(
            aio_pika.Message(
                body=json.dumps({"token": token}).encode("utf-8"),
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=ROUTING_KEY_DONE,
        )

    async def _route_failure(
        self,
        dlx,
        message: AbstractIncomingMessage,
        decision,
        topic_exchange=None,
    ) -> None:
        """Route a failed job to the retry ladder or the dead queue.

        The original message is acked by ``message.process(requeue=False)``
        regardless — routing happens through the DLX publish, never by
        requeueing, so the broker cannot redeliver it in a tight loop.
        """
        if decision.is_retry:
            await self._publish_to_dlx(
                dlx,
                routing_key=f"retry.{decision.tier}",
                body=message.body,
                headers=dict(message.headers or {}),
            )
            _logger.warning(
                "invoice-ai worker: %s -> retry tier %s (attempt %s)",
                decision.reason,
                decision.tier,
                decision.attempt,
            )
        elif decision.is_dead:
            await self._dead_letter(dlx, message, decision.reason, topic_exchange)
        else:
            WORKER_JOBS_TOTAL.labels(status="failed").inc()
            _logger.warning(
                "invoice-ai worker: discarding unclassifiable message: %s",
                decision.reason,
            )

    async def _dead_letter(
        self,
        dlx,
        message: AbstractIncomingMessage,
        reason,
        topic_exchange=None,
    ) -> None:
        """Publish to the poison queue and let the original ack.

        ``reason`` is surfaced as the ``x-death-reason`` header on the dead
        message so the dead queue (and the management UI) shows WHY the job
        was poisoned. When the body carries a correlatable ``job_uuid``, a
        signed ``status:"failed"`` result is ALSO published on the topic
        exchange so the Odoo result consumer can mark the originating outbox
        job dead and flag the move — the dead-letter is visible in the Odoo
        taskboard, not just the management UI.
        """
        headers = dict(message.headers or {})
        headers["x-death-reason"] = str(reason)[:2000]
        await self._publish_to_dlx(
            dlx,
            routing_key=DEAD_ROUTING_KEY,
            body=message.body,
            headers=headers,
        )
        if topic_exchange is not None:
            try:
                body = _parse_body(message)
                job_uuid = body.get("job_uuid") or ""
                move_id = body.get("move_id")
                if job_uuid and move_id:
                    failed_payload = {
                        "job_uuid": job_uuid,
                        "move_id": int(move_id),
                        "status": "failed",
                        "error": str(reason)[:2000],
                    }
                    await self._publish_result(topic_exchange, failed_payload)
            except Exception:
                _logger.exception(
                    "invoice-ai worker: could not publish failed result for "
                    "dead-lettered job",
                )
        WORKER_JOBS_TOTAL.labels(status="dead-lettered").inc()
        _logger.warning("invoice-ai worker: dead-lettered job: %s", reason)

    async def _publish_to_dlx(
        self,
        dlx,
        routing_key: str,
        body: bytes,
        headers: dict | None = None,
    ) -> None:
        await dlx.publish(
            aio_pika.Message(
                body=body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                headers=headers or {},
            ),
            routing_key=routing_key,
        )


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    from .amqp import build_amqp_url

    consumer = InvoiceConsumer()
    await consumer.run(build_amqp_url())


if __name__ == "__main__":
    asyncio.run(main())
