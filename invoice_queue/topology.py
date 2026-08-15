"""Declare the invoice agent RabbitMQ topology (AMQP 0-9-1).

Idempotent topology script for the ``invoice.agent`` topic exchange:

    exchange   invoice.agent   (durable topic, survives broker restarts)
    queue      invoice.extract (durable, bound on ``extract.request``)
    queue      invoice.result  (durable, bound on ``extract.done``)

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

Recipe used across the RabbitMQ tutorials:

1. Open a ``pika.BlockingConnection`` with a single ``pika.URLParameters``
   URL (credentials, host, heartbeat, timeout in one place).
2. Open one channel (a channel is a lightweight multiplexed connection;
   publishers and consumers use their own).
3. ``exchange_declare(exchange, exchange_type='topic', durable=True)`` —
   durable means the exchange survives a broker restart *and* survives on
   the broker even when no consumer is connected.
4. ``queue_declare(queue, durable=True)`` so pending extraction jobs are
   not lost when the broker restarts mid-burst.
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
ROUTING_KEY_REQUEST = "extract.request"
ROUTING_KEY_STARTED = "extract.started"
ROUTING_KEY_DONE = "extract.done"

# What each queue will receive (documented contract — see docs/adr-004):
#   invoice.extract <- extract.request  : JOB REQUEST. Body = {"move_id": N,
#                                         "attachment_id": M, "attempt": K}
#   invoice.result  <- extract.done     : JOB RESULT.  Body = {"move_id": N,
#                                         "status": "done"|"failed",
#                                         "ai_ex...": ...}
QUEUE_BINDINGS = [
    (QUEUE_EXTRACT, ROUTING_KEY_REQUEST),
    # invoice.result receives both lifecycle signals from the worker: the
    # "extracting" start event and the signed "done/failed" result.
    (QUEUE_RESULT, ROUTING_KEY_STARTED),
    (QUEUE_RESULT, ROUTING_KEY_DONE),
]
ROUTING_KEY_STARTED = "extract.started"


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
        for queue_name, routing_key in QUEUE_BINDINGS:
            # queue_declare is idempotent under AMQP 0-9-1: same name +
            # same durable flag is a no-op rather than an error.
            channel.queue_declare(queue=queue_name, durable=True)
            channel.queue_bind(
                queue=queue_name,
                exchange=EXCHANGE_NAME,
                routing_key=routing_key,
            )
            _logger.info("bound %s <- invoice.agent(%s)", queue_name, routing_key)
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
    reports for ``invoice.extract`` and ``invoice.result``. Raises on HTTP
    errors so CI fails loudly when the topology drifted.
    """
    user = os.environ.get("RABBITMQ_USER", "guest")
    password = os.environ.get("RABBITMQ_PASS", "guest")
    results = []
    for queue_name in (QUEUE_EXTRACT, QUEUE_RESULT):
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
