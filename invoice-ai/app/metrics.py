"""Prometheus metrics for the invoice-ai pipeline.

Metric types and why each was chosen:

- **Counter** (monotonically increasing): http_requests_total, claude_tokens_total,
  worker_jobs_total. You can only ``rate()`` or ``increase()`` them, never subtract.
- **Histogram** (bucket-based duration distribution): http_request_duration_seconds,
  ocr_duration_seconds, claude_api_duration_seconds, worker_job_duration_seconds.
  Compute percentiles with ``histogram_quantile(0.95, ...)``.
- **Gauge** (goes up and down): rabbitmq_queue_depth, db_connections_active.

**Cardinality control**: All labels are bounded enums or short strings.
No user IDs, request IDs, or free-form text. This keeps the time series
count predictable and the TSDB healthy.

RED method (for the HTTP service):
  - **R**ate:   ``rate(http_requests_total[5m])``
  - **E**rrors: ``rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])``
  - **D**uration: ``histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))``

USE method (for the EC2 host — handled by node_exporter):
  - **U**tilization: CPU%, memory%, disk%
  - **S**aturation:  load average, swap
  - **E**rrors:      packet drops, disk I/O errors
"""

from __future__ import annotations

import time
from typing import Any

from prometheus_client import Counter, Gauge, Histogram

# ---------------------------------------------------------------------------
# HTTP request metrics — RED method
# ---------------------------------------------------------------------------

HTTP_REQUEST_DURATION = Histogram(
    name="http_request_duration_seconds",
    documentation="Duration of HTTP requests in seconds",
    labelnames=["method", "endpoint", "status"],
    # Bucket boundaries chosen for a web service handling 0.1s–30s requests
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

HTTP_REQUESTS_TOTAL = Counter(
    name="http_requests_total",
    documentation="Total number of HTTP requests",
    labelnames=["method", "endpoint", "status"],
)

# ---------------------------------------------------------------------------
# Invoice pipeline metrics — the core extraction pipeline
# ---------------------------------------------------------------------------

OCR_DURATION = Histogram(
    name="invoice_ocr_duration_seconds",
    documentation="Duration of OCR extraction (PDF/image to text)",
    labelnames=[],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

CLAUDE_API_DURATION = Histogram(
    name="invoice_claude_api_duration_seconds",
    documentation="Round-trip latency of Claude API calls",
    labelnames=["model"],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0, 120.0),
)

CLAUDE_TOKENS_TOTAL = Counter(
    name="invoice_claude_tokens_total",
    documentation="Total tokens consumed by Claude API (input + output)",
    labelnames=["model", "type"],
)

WORKER_JOBS_TOTAL = Counter(
    name="invoice_worker_jobs_total",
    documentation="Total invoice extraction jobs processed by the worker",
    labelnames=["status"],  # "done", "failed", "dead-lettered"
)

WORKER_JOB_DURATION = Histogram(
    name="invoice_worker_job_duration_seconds",
    documentation="End-to-end duration of a worker job (consume → publish result)",
    labelnames=[],
    buckets=(1.0, 2.5, 5.0, 10.0, 20.0, 30.0, 60.0, 120.0, 300.0),
)

# ---------------------------------------------------------------------------
# Infrastructure gauges — current state metrics
# ---------------------------------------------------------------------------

RABBITMQ_QUEUE_DEPTH = Gauge(
    name="invoice_rabbitmq_queue_depth",
    documentation="Current number of messages in the extraction queue",
    labelnames=["queue"],
)

DB_CONNECTIONS_ACTIVE = Gauge(
    name="invoice_db_connections_active",
    documentation="Current number of active database connections",
    labelnames=[],
)

# ---------------------------------------------------------------------------
# Helper context manager for timing
# ---------------------------------------------------------------------------


class Timer:
    """Context manager that records elapsed seconds into a Histogram.

    Usage::

        with CLAUDE_API_DURATION.labels(model="claude-opus-4-8").time():
            result = await client.messages.create(...)
    """

    def __init__(self, histogram: Histogram, **labels: Any) -> None:
        self._histogram = histogram
        self._labels = labels
        self._start: float = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.monotonic()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        elapsed = time.monotonic() - self._start
        if self._labels:
            self._histogram.labels(**self._labels).observe(elapsed)
        else:
            self._histogram.observe(elapsed)


def record_claude_tokens(model: str, usage: dict[str, Any]) -> None:
    """Record token usage from a Claude API response.

    ``usage`` is the dict returned by ``_usage_dict()`` in claude.py:
    ``{input_tokens, cache_creation_input_tokens, cache_read_input_tokens, output_tokens}``.
    """
    input_tokens = usage.get("input_tokens") or 0
    output_tokens = usage.get("output_tokens") or 0
    cache_read = usage.get("cache_read_input_tokens") or 0

    CLAUDE_TOKENS_TOTAL.labels(model=model, type="input").inc(input_tokens)
    CLAUDE_TOKENS_TOTAL.labels(model=model, type="output").inc(output_tokens)
    # Cache reads are billed at 10% — record them separately for cost tracking
    if cache_read:
        CLAUDE_TOKENS_TOTAL.labels(model=model, type="cache_read").inc(cache_read)
