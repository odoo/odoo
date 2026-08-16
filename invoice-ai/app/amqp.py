"""AMQP constants + idempotent topology declare for the aio-pika worker.

Mirrors ``invoice_queue/topology.py`` at the repo root (the authoritative source).
The worker re-declares the topology on every (re)connect: AMQP 0-9-1
declaration is a no-op when name/type/flags match, so this is cheap, safe,
and heals a broker that was reset while the worker slept.

Routing-key namespace (the semantic contract between Odoo, the worker and
the result consumer):

* ``extract.request``  Odoo outbox -> ``invoice.extract``      (job request)
* ``extract.started``  worker     -> ``invoice.result``       (lifecycle: extracting)
* ``extract.done``     worker     -> ``invoice.result``       (lifecycle: ready/failed)
* ``extract.dead``     worker     -> ``invoice.extract.dead`` (poison invoice)

Dead-lettering / retry ladder (v0.9 — contract in docs/queue-contract.md):

* ``invoice.extract`` dead-letters into the direct exchange
  ``invoice.extract.dlx`` (``x-dead-letter-exchange``) with default routing
  key ``extract.dead``, and has ``x-delivery-limit: 3`` — a worker crash
  mid-job redelivers at most 3 times, then the broker routes the message to
  the dead queue. A poison PDF can never loop forever.
* The retry tiers ``retry.5s`` / ``retry.30s`` / ``retry.5m`` sit bound on
  the DLX. Their ``x-message-ttl`` is the backoff delay; expiry dead-letters
  the message back to ``invoice.agent`` on ``extract.request`` so it
  re-enters ``invoice.extract``. No worker timers.
* ``invoice.extract.dead`` binds ``extract.dead`` on both exchanges.
"""

from __future__ import annotations

import logging
from typing import Any

import aio_pika

_logger = logging.getLogger(__name__)

EXCHANGE_NAME = "invoice.agent"
EXCHANGE_TYPE = "topic"
QUEUE_EXTRACT = "invoice.extract"
QUEUE_RESULT = "invoice.result"
QUEUE_DEAD = "invoice.extract.dead"
DLX_EXCHANGE = "invoice.extract.dlx"
DLX_TYPE = "direct"
ROUTING_KEY_REQUEST = "extract.request"
ROUTING_KEY_STARTED = "extract.started"
ROUTING_KEY_DONE = "extract.done"
ROUTING_KEY_DEAD = "extract.dead"

# Retry ladder tiers (name -> TTL ms). Keep in lockstep with
# invoice_queue/topology.py — the TTL is the backoff; expiry re-publishes
# the message to invoice.agent/extract.request.
RETRY_TIERS: list[tuple[str, int]] = [
    ("retry.5s", 5_000),
    ("retry.30s", 30_000),
    ("retry.5m", 300_000),
]
RETRY_KEYS: dict[str, str] = {name: f"retry.{name}" for name, _ in RETRY_TIERS}
DELIVERY_LIMIT = 3

TOPOLOGY_BINDINGS = [
    (QUEUE_EXTRACT, ROUTING_KEY_REQUEST),
    (QUEUE_RESULT, ROUTING_KEY_STARTED),
    (QUEUE_RESULT, ROUTING_KEY_DONE),
    (QUEUE_DEAD, ROUTING_KEY_DEAD),
]

DLX_BINDINGS = [
    (queue_name, RETRY_KEYS[queue_name]) for queue_name, _ in RETRY_TIERS
] + [(QUEUE_DEAD, ROUTING_KEY_DEAD)]


def build_amqp_url() -> str:
    """Build the ``amqp://`` URL from environment (compose forwards these).

    Defaults match the compose ``rabbitmq`` service and its management
    credentials so a local ``python -m app.consumer`` works out of the box
    against a ``docker compose up`` broker.
    """
    import os

    host = os.environ.get("RABBITMQ_HOST", "localhost")
    port = os.environ.get("RABBITMQ_PORT", "5672")
    user = os.environ.get("RABBITMQ_USER", "guest")
    password = os.environ.get("RABBITMQ_PASS", "guest")
    return f"amqp://{user}:{password}@{host}:{port}/"


async def declare_topology(channel: aio_pika.abc.AbstractChannel) -> None:
    """Declare the exchange + queues + bindings on ``channel``.

    Idempotent under AMQP 0-9-1; safe to call on every reconnect. Durable
    primitives survive broker restarts so a job published before the worker
    connects is not lost. The extract queue carries the DLX arguments and
    the delivery limit; the retry tiers carry their TTL and a DLX back to
    the main exchange. Re-declaring with *changed* arguments raises 406
    (PRECONDITION_FAILED) — a deliberate drift check.
    """
    await channel.declare_exchange(
        EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True,
    )
    await channel.declare_exchange(
        DLX_EXCHANGE, aio_pika.ExchangeType.DIRECT, durable=True,
    )
    for queue_name, routing_key in TOPOLOGY_BINDINGS:
        arguments: Any = None
        if queue_name == QUEUE_EXTRACT:
            arguments = {
                "x-dead-letter-exchange": DLX_EXCHANGE,
                "x-dead-letter-routing-key": ROUTING_KEY_DEAD,
                "x-delivery-limit": DELIVERY_LIMIT,
            }
        queue = await channel.declare_queue(
            queue_name, durable=True, arguments=arguments,
        )
        await queue.bind(EXCHANGE_NAME, routing_key=routing_key)
        _logger.debug("bound %s <- invoice.agent(%s)", queue_name, routing_key)

    # Retry tiers: TTL-backed queues on the DLX. The dead queue shares the
    # loop but carries no TTL and no DLX hop — it is the terminal sink.
    ttl_by_queue: dict[str, int] = {name: ttl for name, ttl in RETRY_TIERS}
    for queue_name, routing_key in DLX_BINDINGS:
        retry_arguments: Any = None
        if queue_name in ttl_by_queue:
            retry_arguments = {
                "x-message-ttl": ttl_by_queue[queue_name],
                "x-dead-letter-exchange": EXCHANGE_NAME,
                "x-dead-letter-routing-key": ROUTING_KEY_REQUEST,
                "x-delivery-limit": DELIVERY_LIMIT,
            }
        queue = await channel.declare_queue(
            queue_name, durable=True, arguments=retry_arguments,
        )
        await queue.bind(DLX_EXCHANGE, routing_key=routing_key)
        _logger.debug(
            "bound %s <- invoice.extract.dlx(%s) ttl=%dms",
            queue_name,
            routing_key,
            retry_arguments["x-message-ttl"] if retry_arguments else 0,
        )
