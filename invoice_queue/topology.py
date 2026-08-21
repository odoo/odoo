"""Declare the invoice agent RabbitMQ topology (AMQP 0-9-1).

Idempotent topology script for the ``invoice.agent`` topic exchange:

    exchange     invoice.agent         (durable topic, survives broker restarts)
    exchange     invoice.extract.dlx   (durable direct — dead-letter exchange)
    queue        invoice.extract       (durable, bound on ``extract.request``)
    queue        invoice.result        (durable, bound on ``extract.started``/``extract.done``)
    queue        retry.5s              (durable, TTL 5 s, DLX back to invoice.agent)
    queue        retry.30s             (durable, TTL 30 s, DLX back to invoice.agent)
    queue        retry.5m              (durable, TTL 5 min, DLX back to invoice.agent)
    queue        invoice.extract.dead  (durable — poison invoices land here)

Why topic and not direct/fanout:

* A *direct* exchange routes on the exact routing key you publish with —
  a publisher would need to know the consuming queue's name, coupling
  producer and consumer. The extraction service publishes ``extract.request``
  without caring that ``invoice.extract`` is the queue that consumes it.
* A *fanout* exchange copies every message to every bound queue — it cannot
  express "extraction requests go here, extraction results go there".
* *Topic* gives us both: a ``#`` (multi-segment) or ``*`` (single-segment)
  wildcard lets future consumers bind ``invoice.#`` to observe every
  extraction event, while today's explicit bindings keep the two queues
  isolated. The routing-key namespace (``extract.request`` / ``extract.done``)
  is itself the semantic contract between the Odoo publisher, the worker and
  the result consumer.

Retry ladder / dead-lettering (v0.9 — see docs/queue-contract.md §Retries):

* ``invoice.extract`` is declared with three queue arguments:

  - ``x-dead-letter-exchange: invoice.extract.dlx`` — anything the worker
    rejects (``basic_reject requeue=False``) or that is redelivered past
    ``x-delivery-limit`` is routed through the dead-letter exchange.
  - ``x-dead-letter-routing-key: extract.dead`` — the *default* destination
    when the broker dead-letters autonomously (delivery-limit exceeded).
    The worker overrides this destination explicitly per failure class by
    publishing to the DLX itself with the right routing key.
  - ``x-delivery-limit: 3`` — a worker crash mid-job (message unacked)
    redelivers at most 3 times, then the broker dead-letters it. A corrupt
    PDF that crashes Tesseract can NEVER loop forever redelivering and
    burning Anthropic tokens on every attempt.

* Transient upstream failures (Anthropic 429 rate limit, 5xx, connection
  errors) are routed by the worker into the retry ladder via the DLX:
  ``retry.5s`` -> ``retry.30s`` -> ``retry.5m``. Each retry queue carries
  ``x-message-ttl`` for its tier and ``x-dead-letter-exchange:
  invoice.agent`` with routing key ``extract.request``, so a message whose
  TTL expires is re-published back to the main queue. **The retry delay is
  the queue's TTL — no timers, no sleep, no cron in the worker.**
* Permanent failures (bad schema, malformed body) are routed to
  ``extract.dead`` immediately: retrying can never fix a bad prompt/schema.

The ``invoice.extract.dlx`` exchange is *direct*: every consumer (the
worker republishing and the broker dead-lettering) must name an exact
routing key, which is the retry/poison contract. Direct is the right type
here — there is no fan-out or wildcard semantics on the dead path.

Recipe used across the RabbitMQ tutorials:

1. Open a ``pika.BlockingConnection`` with a single ``pika.URLParameters``
   URL (credentials, host, heartbeat, timeout in one place).
2. Open one channel (a channel is a lightweight multiplexed connection;
   publishers and consumers use their own).
3. ``exchange_declare(exchange, exchange_type=..., durable=True)`` —
   durable means the exchange survives a broker restart *and* survives on
   the broker even when no consumer is connected.
4. ``queue_declare(queue, durable=True, arguments=...)`` so pending
   extraction jobs are not lost when the broker restarts mid-burst.
5. ``queue_bind(queue, exchange, routing_key=...)`` one binding per routing
   key the queue must receive.
6. Close the connection. Declaring is a connection-time concern; consumers
   and publishers open their own channels later.

Usage:

    # From the repo root, with RABBITMQ_HOST/USER/PASS in the environment
    # (docker-compose exports these into every container):
    python invoice_queue/topology.py

    # Or as a module:
    python -m invoice_queue.topology

    # Point at a custom broker:
    RABBITMQ_HOST=localhost RABBITMQ_PORT=5672 RABBITMQ_USER=guest \\
        RABBITMQ_PASS=guest python invoice_queue/topology.py

The script is idempotent: re-running it re-declares the same primitive
(AMQP 0-9-1 declaration is a no-op when the name, type and flags match) and
is safe to run from CI or a ``depends_on``-gated init container on every
broker start.
"""

import base64
import json
import logging
import os
import sys
import urllib.error
import urllib.request

import pika

_logger = logging.getLogger("invoice_queue.topology")

# --- topology constants ------------------------------------------------------
# These are the source of truth for the invoice agent contract. Consumers
# and publishers (the queue.publisher Odoo model and the AI worker) must
# reference the same exchange/queue/keys — try to keep the strings in sync.
EXCHANGE_NAME = "invoice.agent"
EXCHANGE_TYPE = "topic"
QUEUE_EXTRACT = "invoice.extract"
QUEUE_RESULT = "invoice.result"
QUEUE_DEAD = "invoice.extract.dead"
# v0.10: RAG embed jobs. The Odoo outbox publishes embed.request; the
# worker answers by calling /v1/embed and publishing a signed embed.done
# result back on invoice.result.
QUEUE_EMBED = "invoice.embed"
DLX_EXCHANGE = "invoice.extract.dlx"
DLX_TYPE = "direct"
ROUTING_KEY_REQUEST = "extract.request"
ROUTING_KEY_STARTED = "extract.started"
ROUTING_KEY_DONE = "extract.done"
ROUTING_KEY_DEAD = "extract.dead"
ROUTING_KEY_EMBED_REQUEST = "embed.request"
ROUTING_KEY_EMBED_DONE = "embed.done"

# Retry ladder (v0.9): tier name -> TTL milliseconds. A transient failure is
# routed to the tier selected by the attempt counter (see app/retry.py in
# invoice-ai). Each tier's TTL is the backoff delay; expiry dead-letters the
# message back to invoice.agent on ``extract.request`` so it re-enters
# invoice.extract.
RETRY_TIERS: list[tuple[str, int]] = [
    ("retry.5s", 5_000),
    ("retry.30s", 30_000),
    ("retry.5m", 300_000),
]
RETRY_KEYS: dict[str, str] = {name: f"retry.{name}" for name, _ in RETRY_TIERS}
# Total timeout window across the whole ladder: 5 s + 30 s + 5 m. A message
# that failed every tier is not retried again — next stop is the dead queue.
MAX_RETRY_ATTEMPTS = len(RETRY_TIERS)

# Safety net for crash-redelivery (unacked messages). A worker killed
# mid-job redelivers at most 3 times; the broker then dead-letters the
# message via the DLX with the queue's default routing key (extract.dead).
# This is what makes a poison PDF that crashes Tesseract IMPOSSIBLE to loop
# forever while burning Anthropic tokens on every attempt.
DELIVERY_LIMIT = 3

# What each queue will receive (wiring contract — see docs/queue-contract.md):
#   invoice.extract <- extract.request : JOB REQUEST. Body = {"move_id": N,
#                                        "attachment_id": M, "attempt": K,
#                                        "job_uuid": "...", "ocr_text": "..."}
#   invoice.result  <- extract.done    : JOB RESULT.  Body = {"token": "<jwt>"}
#                                        — signed HS256 with the shared secret;
#                                        claims carry the parsed extraction.
#   retry.*         (DLX binding)      : transient-failure retries, TTL-backed
#   invoice.extract.dead <- extract.dead : poison messages (x-death inspectable)
QUEUE_BINDINGS = [
    (QUEUE_EXTRACT, ROUTING_KEY_REQUEST),
    # invoice.result receives both lifecycle signals from the worker: the
    # "extracting" start event and the signed "done/failed" result.
    (QUEUE_RESULT, ROUTING_KEY_STARTED),
    (QUEUE_RESULT, ROUTING_KEY_DONE),
    # Dead-letter exchange bindings. The main queue's DLX argument routes
    # here; the dead queue binds the poison key.
    (QUEUE_DEAD, ROUTING_KEY_DEAD),
]

# Retry queues are bound on the DLX exchange with their own routing keys.
DLX_BINDINGS = [
    (queue_name, RETRY_KEYS[queue_name]) for queue_name, _ in RETRY_TIERS
] + [(QUEUE_DEAD, ROUTING_KEY_DEAD)]

# Queue arguments for the retry tiers. ``x-dead-letter-exchange`` points
# back at the invoice.agent topic exchange; the routing key on expiry is
# ``extract.request``, so the message re-enters the main queue — the TTL is
# the retry backoff. Durable so the tier survives broker restarts.


def _retry_queue_arguments() -> list[dict]:
    # Classic queues: the retry ladder needs x-message-ttl, which quorum
    # queues do not support. No x-delivery-limit here — RabbitMQ only
    # accepts it on quorum queues, and each retry message is a fresh
    # single hop (the worker acks the original before publishing it).
    return [
        {
            "x-message-ttl": ttl_ms,
            "x-dead-letter-exchange": EXCHANGE_NAME,
            "x-dead-letter-routing-key": ROUTING_KEY_REQUEST,
        }
        for _, ttl_ms in RETRY_TIERS
    ]


def connection_parameters():
    """Build ``pika.ConnectionParameters`` from the environment.

    ``docker-compose`` injects ``RABBITMQ_USER`` / ``RABBITMQ_PASS`` /
    ``RABBITMQ_HOST`` into every service; standalone runs fall back to the
    RabbitMQ management-plugin defaults (``guest``/``guest``@localhost).
    """
    host = os.environ.get("RABBITMQ_HOST", "localhost")
    port = int(os.environ.get("RABBITMQ_PORT", "5672"))
    user = os.environ.get("RABBITMQ_USER", "guest")
    password = os.environ.get("RABBITMQ_PASS", "guest")
    heartbeat = int(os.environ.get("RABBITMQ_HEARTBEAT", "60"))
    return pika.ConnectionParameters(
        host=host,
        port=port,
        credentials=pika.PlainCredentials(user, password),
        heartbeat=heartbeat,
        connection_attempts=3,
        retry_delay=2,
        blocked_connection_timeout=30,
    )


def declare_topology(connection=None):
    """Declare exchange + queues + bindings on the given opened connection.

    ``connection`` may be ``None`` (a ``BlockingConnection`` is created and
    closed around the declarations) or an already-opened connection whose
    channel is reused. Returns ``None``; raises ``pika.exceptions.AMQPError``
    subclasses on broker/network failure.

    The explicit ``durable=True`` on every primitive is the whole point: an
    extraction request must survive a broker restart and must exist before
    any publisher or consumer connects, so no message is ever dropped because
    the exchange or queue did not exist yet.
    """
    own_connection = connection is None
    if own_connection:
        connection = pika.BlockingConnection(connection_parameters())

    try:
        channel = connection.channel()
        channel.exchange_declare(
            exchange=EXCHANGE_NAME,
            exchange_type=EXCHANGE_TYPE,
            durable=True,
        )
        # The dead-letter exchange (direct). The main extract queue dead-
        # letters into it; the worker publishes retry/poison routes into it.
        channel.exchange_declare(
            exchange=DLX_EXCHANGE,
            exchange_type=DLX_TYPE,
            durable=True,
        )
        for queue_name, routing_key in QUEUE_BINDINGS:
            # queue_declare is idempotent under AMQP 0-9-1: same name +
            # same durable flag + same arguments is a no-op rather than an
            # error. Re-declaring with *changed* arguments raises 406
            # (PRECONDITION_FAILED) — an intentional safety net that catches
            # a drifted topology contract instead of silently mutating it.
            queue_arguments = None
            if queue_name == QUEUE_EXTRACT:
                # Quorum queue: RabbitMQ 3.13 only honors x-delivery-limit
                # on quorum queues (it rejects the argument on classic
                # queues with PRECONDITION_FAILED).
                queue_arguments = {
                    "x-queue-type": "quorum",
                    "x-dead-letter-exchange": DLX_EXCHANGE,
                    "x-dead-letter-routing-key": ROUTING_KEY_DEAD,
                    "x-delivery-limit": DELIVERY_LIMIT,
                }
            channel.queue_declare(queue=queue_name, durable=True, arguments=queue_arguments)
            channel.queue_bind(
                queue=queue_name,
                exchange=EXCHANGE_NAME,
                routing_key=routing_key,
            )
            _logger.info("bound %s <- invoice.agent(%s)", queue_name, routing_key)

        # Retry tiers: TTL-backed queues on the DLX. Their expiry re-publishes
        # the message to invoice.agent/extract.request (see _retry_queue_arguments),
        # which is the entire retry mechanism — no worker timers.
        for (queue_name, routing_key), arguments in zip(DLX_BINDINGS, _retry_queue_arguments()):
            channel.queue_declare(queue=queue_name, durable=True, arguments=arguments)
            channel.queue_bind(
                queue=queue_name,
                exchange=DLX_EXCHANGE,
                routing_key=routing_key,
            )
            _logger.info(
                "bound %s <- invoice.extract.dlx(%s) ttl=%dms",
                queue_name,
                routing_key,
                arguments["x-message-ttl"],
            )
    finally:
        if own_connection:
            connection.close()


def verify_bindings(base_url):
    """Verify the declared bindings through the RabbitMQ Management HTTP API.

    ``base_url`` is the management API root, e.g. ``http://localhost:15672``
    (the ``rabbitmq:3.13-management`` image exposes it). Uses the same
    credentials as the AMQP connection — the management API authenticates
    with the same ``RABBITMQ_DEFAULT_USER`` / ``RABBITMQ_DEFAULT_PASS`` used
    for the AMQP protocol itself.

    Returns the list of ``(queue, routing_key, exchange)`` tuples the broker
    reports for every queue in the contract. Raises on HTTP errors so CI
    fails loudly when the topology drifted.
    """
    user = os.environ.get("RABBITMQ_USER", "guest")
    password = os.environ.get("RABBITMQ_PASS", "guest")
    results = []
    for queue_name in (QUEUE_EXTRACT, QUEUE_RESULT, QUEUE_DEAD,
                       *(name for name, _ in RETRY_TIERS)):
        url = f"{base_url.rstrip('/')}/api/queues/%2F/{queue_name}/bindings"
        # RabbitMQ's management API uses URL-encoded vhost in the path; %2F
        # is the default "/" vhost. urllib does not re-encode already-encoded
        # slashes, so %2F passes through intact.
        request = urllib.request.Request(url)
        credentials = base64.b64encode(f"{user}:{password}".encode()).decode()
        request.add_header("Authorization", f"Basic {credentials}")
        with urllib.request.urlopen(request, timeout=10) as response:
            bindings = json.load(response)
        for binding in bindings:
            results.append(
                (
                    binding.get("queue"),
                    binding.get("routing_key"),
                    binding.get("source"),
                ),
            )
        _logger.info(
            "management API: %s bound on %s",
            queue_name,
            [b.get("routing_key") for b in bindings],
        )
    return results


def inspect_dead_letter(queue_name=QUEUE_DEAD, base_url=None, limit=1):
    """Fetch the newest dead-lettered messages and print their ``x-death``.

    ``x-death`` is RabbitMQ's per-message audit header, stamped on every
    dead-letter hop: `[{"count": N, "exchange": ..., "queue": ...,
    "reason": ..., "routing-keys": [...], "time": ...}]`. Inspecting it is
    how you prove a poison invoice was dead-lettered the exact number of
    expected times and no more.

    Uses the management API ``/api/queues/%2F/<queue>/get`` with
    ``ackmode=ack_requeue_true`` so the message is NOT consumed — this is a
    read-only exercise. Returns the list of message dicts (or raises).
    """
    base_url = base_url or os.environ.get(
        "RABBITMQ_MANAGEMENT_URL", "http://localhost:15672",
    )
    user = os.environ.get("RABBITMQ_USER", "guest")
    password = os.environ.get("RABBITMQ_PASS", "guest")
    url = f"{base_url.rstrip('/')}/api/queues/%2F/{queue_name}/get"
    body = json.dumps({"count": limit, "ackmode": "ack_requeue_true",
                       "encoding": "auto"}).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    credentials = base64.b64encode(f"{user}:{password}".encode()).decode()
    request.add_header("Authorization", f"Basic {credentials}")
    with urllib.request.urlopen(request, timeout=10) as response:
        messages = json.load(response)
    for message in messages:
        headers = message.get("properties", {}).get("headers") or {}
        _logger.info(
            "dead-letter %s: x-death=%s routing_key=%s",
            queue_name,
            json.dumps(headers.get("x-death"), default=str),
            message.get("routing_key"),
        )
    return messages


def main():
    """CLI entry point: declare the topology, then verify via the API."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    declare_topology()

    # Verification step — the task brief asks to check bindings via the
    # management API after declaring them. Fail loudly if the API is not
    # reachable OR the bindings do not match the contract.
    api_url = os.environ.get(
        "RABBITMQ_MANAGEMENT_URL",
        "http://localhost:15672",
    )
    try:
        bindings = verify_bindings(api_url)
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        _logger.error(
            "topology declared, but management API verification failed at %s: %s",
            api_url,
            exc,
        )
        return 1

    expected = [
        (QUEUE_EXTRACT, ROUTING_KEY_REQUEST, EXCHANGE_NAME),
        (QUEUE_RESULT, ROUTING_KEY_STARTED, EXCHANGE_NAME),
        (QUEUE_RESULT, ROUTING_KEY_DONE, EXCHANGE_NAME),
        (QUEUE_DEAD, ROUTING_KEY_DEAD, EXCHANGE_NAME),
        (QUEUE_DEAD, ROUTING_KEY_DEAD, DLX_EXCHANGE),
    ]
    expected += [
        (queue_name, RETRY_KEYS[queue_name], DLX_EXCHANGE)
        for queue_name, _ in RETRY_TIERS
    ]
    actual = sorted(
        (queue_name, routing_key, exchange)
        for queue_name, routing_key, exchange in bindings
    )
    if actual != sorted(expected):
        _logger.error("binding drift: expected %s, broker reports %s", expected, actual)
        return 1

    _logger.info("topology verified against management API: %s", expected)
    return 0


if __name__ == "__main__":
    sys.exit(main())
