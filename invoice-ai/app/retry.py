"""Failure classification for the worker's retry ladder.

Pure decision logic, deliberately free of any broker or SDK dependency so
it unit-tests with a fake broker and no RabbitMQ. The consumer
(``app/consumer.py``) calls the two functions here and executes the
returned decision against aio-pika.

Contract with ``invoice_queue/topology.py`` (the authoritative topology):

* ``invoice.extract`` has ``x-delivery-limit: 3`` and dead-letters into
  ``invoice.extract.dlx`` (direct exchange).
* The retry tiers sit bound on the DLX: ``retry.5s`` / ``retry.30s`` /
  ``retry.5m``, each with an ``x-message-ttl`` equal to its tier's backoff.
  TTL expiry re-publishes to ``invoice.agent`` on ``extract.request``, so
  the message re-enters the main queue — **the TTL IS the backoff**.
* ``invoice.extract.dead`` is the poison queue (bound ``extract.dead``).
* ``MAX_RETRY_ATTEMPTS == len(RETRY_TIERS)`` — after exhausting every tier
  a still-transient failure is dead-lettered, never retried again.

Failure classes:

* **Transient** — ``ClaudeRateLimitError`` (Anthropic 429) and
  ``ClaudeUpstreamError`` (5xx / ``APIConnectionError``, which
  ``app/claude.py::_map_upstream_error`` already normalizes). Retrying CAN
  fix these, so they ride the ladder.
* **Permanent** — ``BadRequestError`` / ``ExtractionValidationError`` /
  malformed message bodies. Retrying never fixes a bad schema or a corrupt
  payload; they go straight to the dead queue so they never burn an
  Anthropic call again.
"""

from __future__ import annotations

from dataclasses import dataclass

from .errors import (
    BadRequestError,
    ClaudeRateLimitError,
    ClaudeUpstreamError,
    ExtractionValidationError,
)

# Mirrors invoice_queue/topology.py — keep in lockstep.
RETRY_TIER_5S = "retry.5s"
RETRY_TIER_30S = "retry.30s"
RETRY_TIER_5M = "retry.5m"
RETRY_TIERS: tuple[str, ...] = (RETRY_TIER_5S, RETRY_TIER_30S, RETRY_TIER_5M)
MAX_RETRY_ATTEMPTS = len(RETRY_TIERS)

DEAD_ROUTING_KEY = "extract.dead"
DLX_EXCHANGE = "invoice.extract.dlx"
ROUTING_KEY_REQUEST = "extract.request"
EXCHANGE_NAME = "invoice.agent"

# How many times a message is retried across the whole ladder before being
# dropped to the dead queue even for transient failures.
MAX_TOTAL_ATTEMPTS = MAX_RETRY_ATTEMPTS + 1  # first try + 3 retries


@dataclass(frozen=True)
class RetryDecision:
    """What the consumer must do with a failed message.

    ``route`` is either ``"retry"`` (publish to a retry tier and ack the
    original) or ``"dead"`` (publish ``extract.dead`` and ack the original).
    A ``"discard"`` route means the message is simply acked with no
    republish (used for malformed bodies that cannot even be classified).
    """

    route: str  # "retry" | "dead" | "discard"
    tier: str | None = None
    attempt: int | None = None
    reason: str = ""

    @property
    def is_retry(self) -> bool:
        return self.route == "retry"

    @property
    def is_dead(self) -> bool:
        return self.route == "dead"


def tier_for_attempt(attempt: int) -> str:
    """Return the retry tier for a given 1-based attempt counter.

    Attempt 1 (first failure) -> ``retry.5s``.
    Attempt 2 -> ``retry.30s``.
    Attempt 3 -> ``retry.5m``.
    Attempt >= 4 -> raises ``RetryExhausted`` — every tier was used.
    """
    if attempt < 1:
        attempt = 1
    index = attempt - 1
    if index >= len(RETRY_TIERS):
        raise RetryExhausted(
            f"attempt {attempt} exceeds the {len(RETRY_TIERS)}-tier ladder",
        )
    return RETRY_TIERS[index]


class RetryExhausted(Exception):
    """Raised when no retry tier remains for the attempt counter."""


def is_transient(exc: Exception) -> bool:
    """True when retrying the job can plausibly succeed."""
    return isinstance(exc, (ClaudeRateLimitError, ClaudeUpstreamError))


def is_permanent(exc: Exception) -> bool:
    """True when retrying can never fix the failure."""
    return isinstance(exc, (BadRequestError, ExtractionValidationError))


def classify_failure(exc: Exception, attempt: int | None = None) -> RetryDecision:
    """Classify a worker exception into a retry or dead-letter decision.

    :param exc: the exception raised while processing the job.
    :param attempt: 1-based job attempt counter from the message body. When
        missing (malformed body), the message is discarded — there is no
        trustworthy counter to route on.
    """
    if attempt is None:
        return RetryDecision(
            route="discard",
            reason=f"unclassifiable job (no attempt counter): {exc}",
        )
    if is_transient(exc):
        try:
            tier = tier_for_attempt(attempt)
        except RetryExhausted:
            return RetryDecision(
                route="dead",
                attempt=attempt,
                reason=(
                    f"transient failure {type(exc).__name__} exhausted the "
                    f"{MAX_RETRY_ATTEMPTS}-tier ladder"
                ),
            )
        return RetryDecision(
            route="retry",
            tier=tier,
            attempt=attempt,
            reason=f"transient {type(exc).__name__}: {exc}",
        )
    if is_permanent(exc):
        return RetryDecision(
            route="dead",
            attempt=attempt,
            reason=f"permanent {type(exc).__name__}: {exc}",
        )
    # Unknown exception type — be conservative: dead-letter instead of
    # loop-retrying something the code does not understand.
    return RetryDecision(
        route="dead",
        attempt=attempt,
        reason=f"unexpected {type(exc).__name__}: {exc}",
    )


def attempt_from_body(body: dict) -> int | None:
    """Return the 1-based attempt counter from a job body.

    The published body carries ``attempt`` (see
    ``queue_publisher.publish_extract_request``). ``x-death`` is a fallback
    source when the body predates the field: the worker always echoes the
    attempt back in ``extract.done``.
    """
    raw = body.get("attempt")
    if raw is None:
        return None
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return None
