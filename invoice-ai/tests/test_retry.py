"""Tests for the worker's retry ladder and dead-letter routing.

Two layers are covered:

1. **Pure decision logic** (``app/retry.py``): failure classification,
   tier selection, attempt parsing — no broker involved.
2. **Consumer routing** (``app/consumer.py``): the worker must publish
   transient failures to the correct retry tier on the DLX, permanent
   failures to ``extract.dead``, and happy-path results as a signed
   ``extract.done`` on the topic exchange — exercised with a fake Claude
   and a fake "broker" (a recording stub channel), never RabbitMQ,
   never Anthropic.
"""

import json

import pytest

from app.consumer import InvoiceConsumer, WorkerError, _parse_body
from app.errors import (
    BadRequestError,
    ClaudeRateLimitError,
    ClaudeUpstreamError,
    ExtractionValidationError,
)
from app.retry import (
    MAX_RETRY_ATTEMPTS,
    RetryExhausted,
    attempt_from_body,
    classify_failure,
    tier_for_attempt,
)


# ---------------------------------------------------------------------------
# Pure decision logic — app/retry.py
# ---------------------------------------------------------------------------
class TestRetryDecision:
    def test_rate_limit_routes_to_first_tier(self):
        decision = classify_failure(ClaudeRateLimitError(), attempt=1)
        assert decision.is_retry
        assert decision.tier == "retry.5s"
        assert decision.attempt == 1

    def test_upstream_error_routes_to_second_tier(self):
        decision = classify_failure(ClaudeUpstreamError("5xx"), attempt=2)
        assert decision.is_retry
        assert decision.tier == "retry.30s"
        assert decision.attempt == 2

    def test_third_attempt_routes_to_5m_tier(self):
        decision = classify_failure(ClaudeUpstreamError("5xx"), attempt=3)
        assert decision.is_retry
        assert decision.tier == "retry.5m"

    def test_bad_request_dead_letters_immediately(self):
        decision = classify_failure(BadRequestError("bad schema"), attempt=1)
        assert decision.is_dead
        assert not decision.is_retry
        assert "permanent" in decision.reason

    def test_validation_error_dead_letters_immediately(self):
        decision = classify_failure(ExtractionValidationError("bad json"), attempt=2)
        assert decision.is_dead

    def test_transient_exhausts_ladder_dead_letters(self):
        decision = classify_failure(
            ClaudeRateLimitError(),
            attempt=MAX_RETRY_ATTEMPTS + 1,
        )
        assert decision.is_dead
        assert "exhausted" in decision.reason

    def test_unknown_exception_dead_letters_conservatively(self):
        decision = classify_failure(RuntimeError("weird"), attempt=1)
        assert decision.is_dead
        assert "unexpected" in decision.reason

    def test_missing_attempt_discards(self):
        decision = classify_failure(ClaudeRateLimitError(), attempt=None)
        assert decision.route == "discard"


class TestTierForAttempt:
    def test_tier_mapping(self):
        assert tier_for_attempt(1) == "retry.5s"
        assert tier_for_attempt(2) == "retry.30s"
        assert tier_for_attempt(3) == "retry.5m"

    def test_attempt_below_one_clamps(self):
        assert tier_for_attempt(0) == "retry.5s"

    def test_exhausted_raises(self):
        with pytest.raises(RetryExhausted):
            tier_for_attempt(MAX_RETRY_ATTEMPTS + 1)


class TestAttemptFromBody:
    def test_reads_attempt_field(self):
        assert attempt_from_body({"attempt": 2, "move_id": 12}) == 2

    def test_missing_or_invalid_returns_none(self):
        assert attempt_from_body({"move_id": 12}) is None
        assert attempt_from_body({"attempt": "abc", "move_id": 12}) is None


# ---------------------------------------------------------------------------
# Consumer routing — app/consumer.py with a recording fake channel
# ---------------------------------------------------------------------------
class FakePublished:
    """Records one publish issued against the fake channel."""

    def __init__(self, exchange, routing_key, body, headers):
        self.exchange = exchange
        self.routing_key = routing_key
        self.body = body
        self.headers = headers or {}


class FakeExchange:
    def __init__(self, name, records):
        self.name = name
        self._records = records

    async def publish(self, message, routing_key):
        self._records.append(
            FakePublished(
                self.name,
                routing_key,
                message.body,
                message.headers,
            ),
        )


class FakeChannel:
    """Records exchanges passed to the consumer and the published messages."""

    def __init__(self):
        self.records: list[FakePublished] = []
        self.default_exchange = None
        self.topic = FakeExchange("invoice.agent", self.records)
        self.dlx = FakeExchange("invoice.extract.dlx", self.records)

    async def publish(self, exchange, routing_key, body):
        self.records.append(FakePublished(exchange, routing_key, body, {}))


class _FakeProcessContext:
    """Async context manager mirroring aio-pika's message.process()."""

    def __init__(self, message):
        self._message = message

    async def __aenter__(self):
        return self._message

    async def __aexit__(self, *exc):
        return False


class FakeMessage:
    """Mirrors the aio-pika message surface the consumer touches."""

    def __init__(self, body: bytes, headers=None):
        self.body = body
        self.headers = headers or {}

    def process(self, requeue=False):
        return _FakeProcessContext(self)


class _FakeCfg:
    """Mirrors the Settings surface the consumer reads on ClaudeService."""

    anthropic_model = "claude-opus-4-8"


class FakeClaude:
    """Stand-in for ClaudeService — never touches the SDK."""

    def __init__(self, result=None, error=None):
        self.result_value = result
        self.error = error
        self.calls: list[dict] = []
        # Consumer reads ``claude._cfg.anthropic_model`` for the LLM cache
        # key — mirror the real ClaudeService surface.
        self._cfg = _FakeCfg()

    async def extract(self, text, effort="normal"):
        self.calls.append({"text": text, "effort": effort})
        if self.error:
            raise self.error
        return self.result_value


def _job_body(**overrides):
    body = {
        "move_id": 12,
        "attachment_id": 34,
        "attempt": 1,
        "job_uuid": "uuid-123",
        "ocr_text": "ACME SUPPLIES LLC\nTOTAL USD 1,350.00",
    }
    body.update(overrides)
    return body


def _done_result():
    return {
        "parsed": type(
            "Parsed",
            (),
            {
                "model_dump": lambda self, **kw: {
                    "vendor_name": "ACME",
                    "amount_total": "1350.00",
                }
            },
        )(),
        "usage": {"input_tokens": 10, "output_tokens": 5},
        "model": "claude-opus-4-8",
    }


@pytest.mark.anyio
async def test_happy_path_publishes_signed_done():
    channel = FakeChannel()
    consumer = InvoiceConsumer(
        claude=FakeClaude(result=_done_result()),
        sign=lambda payload: f"signed.{payload['job_uuid']}",
    )
    message = FakeMessage(json.dumps(_job_body()).encode("utf-8"))

    await consumer._handle_message(channel, message, channel.topic, channel.dlx)

    # Two publishes: extract.started on topic, extract.done on topic.
    assert len(channel.records) == 2
    started = channel.records[0]
    assert started.exchange == "invoice.agent"
    assert started.routing_key == "extract.started"
    done = channel.records[1]
    assert done.exchange == "invoice.agent"
    assert done.routing_key == "extract.done"
    body = json.loads(done.body)
    assert body["token"] == "signed.uuid-123"


@pytest.mark.anyio
async def test_rate_limit_routes_to_retry_tier():
    channel = FakeChannel()
    consumer = InvoiceConsumer(
        claude=FakeClaude(error=ClaudeRateLimitError(retry_after_seconds=17)),
        sign=lambda payload: "signed",
    )
    message = FakeMessage(json.dumps(_job_body(attempt=1)).encode("utf-8"))

    await consumer._handle_message(channel, message, channel.topic, channel.dlx)

    assert len(channel.records) == 2  # started + retry publish
    retry = channel.records[1]
    assert retry.exchange == "invoice.extract.dlx"
    assert retry.routing_key == "retry.retry.5s"


@pytest.mark.anyio
async def test_bad_request_dead_letters():
    channel = FakeChannel()
    consumer = InvoiceConsumer(
        claude=FakeClaude(error=BadRequestError("bad schema")),
        sign=lambda payload: "signed",
    )
    message = FakeMessage(json.dumps(_job_body(attempt=1)).encode("utf-8"))

    await consumer._handle_message(channel, message, channel.topic, channel.dlx)

    # started + dead-letter publish + signed failed result
    assert len(channel.records) == 3
    dead = channel.records[1]
    assert dead.exchange == "invoice.extract.dlx"
    assert dead.routing_key == "extract.dead"
    assert "x-death-reason" in dead.headers
    failed = channel.records[2]
    assert failed.exchange == "invoice.agent"
    assert failed.routing_key == "extract.done"
    failed_body = json.loads(failed.body)
    assert failed_body["token"] == "signed"


@pytest.mark.anyio
async def test_malformed_json_dead_letters():
    channel = FakeChannel()
    consumer = InvoiceConsumer(
        claude=FakeClaude(result=_done_result()),
        sign=lambda payload: "signed",
    )
    message = FakeMessage(b"not-json{{{")

    await consumer._handle_message(channel, message, channel.topic, channel.dlx)

    # Malformed body: no job_uuid to correlate -> dead-letter publish only.
    assert len(channel.records) == 1
    assert channel.records[0].routing_key == "extract.dead"


@pytest.mark.anyio
async def test_missing_job_uuid_dead_letters():
    channel = FakeChannel()
    consumer = InvoiceConsumer(
        claude=FakeClaude(result=_done_result()),
        sign=lambda payload: "signed",
    )
    message = FakeMessage(json.dumps(_job_body(job_uuid="")).encode("utf-8"))

    await consumer._handle_message(channel, message, channel.topic, channel.dlx)

    assert len(channel.records) == 1
    assert channel.records[0].routing_key == "extract.dead"


def test_parse_body_rejects_non_object():
    message = FakeMessage(b"[1, 2]")
    with pytest.raises(WorkerError):
        _parse_body(message)
