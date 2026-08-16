"""AMQP constants + idempotent topology declare for the aio-pika worker.

Mirrors ``invoice_queue/topology.py`` at the repo root (the authoritative source).
The worker re-declares the topology on every (re)connect: AMQP 0-9-1
declaration is a no-op when name/type/flags match, so this is cheap, safe,
and heals a broker that was reset while the worker slept.

Routing-key namespace (the semantic contract between Odoo, the worker and
the result consumer):

* ``extract.request``  Odoo outbox -> ``invoice.extract``   (job request)
* ``extract.started``  worker     -> ``invoice.result``    (lifecycle: extracting)
* ``extract.done``     worker     -> ``invoice.result``    (lifecycle: ready/failed)
"""

from __future__ import annotations

import logging

import aio_pika

_logger = logging.getLogger(__name__)

EXCHANGE_NAME = "invoice.agent"
EXCHANGE_TYPE = "topic"
QUEUE_EXTRACT = "invoice.extract"
QUEUE_RESULT = "invoice.result"
ROUTING_KEY_REQUEST = "extract.request"
ROUTING_KEY_STARTED = "extract.started"
ROUTING_KEY_DONE = "extract.done"

TOPOLOGY_BINDINGS = [
    (QUEUE_EXTRACT, ROUTING_KEY_REQUEST),
    (QUEUE_RESULT, ROUTING_KEY_STARTED),
    (QUEUE_RESULT, ROUTING_KEY_DONE),
]


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
    connects is not lost.
    """
    await channel.declare_exchange(
        EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True,
    )
    for queue_name, routing_key in TOPOLOGY_BINDINGS:
        queue = await channel.declare_queue(queue_name, durable=True)
        await queue.bind(EXCHANGE_NAME, routing_key=routing_key)
        _logger.debug("bound %s <- invoice.agent(%s)", queue_name, routing_key)
