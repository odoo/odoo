"""RabbitMQ publisher — thin pika wrapper for the invoice agent queues.

This is the *publishing* half of the AMQP 0-9-1 contract (the topology is
declared by ``invoice_queue/topology.py`` at the repo root). It exists so callers
never touch pika directly:

* ``publish(routing_key, body, exchange=...)`` serializes ``body`` to JSON,
  opens a short-lived ``pika.BlockingConnection``, publishes with
  ``delivery_mode=2`` (persistent message — survives broker restarts) and
  closes the connection.
* A connection is opened *per publish*. That deliberately trades a little
  latency for correctness in the Odoo process model: the connection lives
  inside the HTTP request; it cannot leak or go stale across requests, and
  a blocked/paused broker cannot wedge an idle worker. A commit-time outbox
  (``invoice.agent.job``) is what keeps calls cheap and safe at scale.
* Failure is loud and typed: a missing/secret-less config raises
  ``UserError`` (admin must fix Settings → Invoice Agent), an
  unreachable/refused broker raises ``QueueUnavailable`` — the caller
  decides whether to fail the transaction or leave the outbox row unsent
  (the outbox cron retries it).

Why not a long-lived publisher in ``odoo`` launch? Because a worker's
lifetime is not the process's lifetime, and a message published inside a
transaction that later rolls back is an orphan job — see
``docs/adr-004-rabbitmq.md`` for the full transactional-outbox argument.

Environment contract (mirrors ``invoice_queue/topology.py``):

* ``RABBITMQ_HOST`` (default ``rabbitmq`` — the compose service name, so it
  resolves on the private Docker network with zero configuration)
* ``RABBITMQ_PORT`` (default 5672)
* ``RABBITMQ_USER`` (compose injects ``RABBITMQ_DEFAULT_USER`` from .env)
* ``RABBITMQ_PASS`` (compose injects ``RABBITMQ_DEFAULT_PASS`` from .env)

Import safety mirrors ``models/invoice_extraction.py``: ``pika`` ships inside
the rebuilt odoo image (added to requirements.txt). On a stale image the
module still imports — any publish attempt raises ``QueueUnavailable`` with a
clear "rebuild the image" message instead of crashing the addon load.
"""

import json
import logging
import os

from odoo import _, api, models

_logger = logging.getLogger(__name__)

try:
    import pika
    import pika.exceptions

    _PIKA_AVAILABLE = True
except ImportError:  # pragma: no cover — stale image without pika
    pika = None  # type: ignore[assignment]
    _PIKA_AVAILABLE = False
    _logger.warning(
        "invoice_agent: pika is not installed — queue publishing is disabled. "
        "Rebuild the odoo image (docker compose build odoo) so AMQP jobs can "
        "be published to RabbitMQ.",
    )

# Exchange/routing keys — must match invoice_queue/topology.py (single source of
# truth lives there; mirrored here so the addon can be imported standalone).
EXCHANGE_NAME = "invoice.agent"
ROUTING_KEY_REQUEST = "extract.request"
ROUTING_KEY_DONE = "extract.done"
# v0.10: RAG embed jobs — the Odoo outbox publishes embed.request for the
# worker to embed one vendor-doc text via /v1/embed (the worker answers
# with a signed embed.done result on invoice.result).
ROUTING_KEY_EMBED_REQUEST = "embed.request"
ROUTING_KEY_EMBED_DONE = "embed.done"


class QueueUnavailable(Exception):
    """Raised when the broker is unreachable or refuses the publish.

    Deliberately distinct from ``UserError``: the transactional outbox
    (``invoice.agent.job``) catches this type and leaves the job row unsent
    for the cron to retry, instead of bubbling a user-facing error into a
    commit-time publish.
    """


class QueuePublisher(models.AbstractModel):
    _name = "queue.publisher"
    _description = "RabbitMQ publisher for the invoice agent (AMQP 0-9-1)"

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------
    @api.model
    def _connection_params(self):
        """Build pika.ConnectionParameters from the environment.

        Defaults match compose: ``RABBITMQ_HOST=rabbitmq`` resolves on the
        private Docker network. Credentials come from ``RABBITMQ_DEFAULT_USER``
        / ``RABBITMQ_DEFAULT_PASS`` which docker-compose forwards into every
        container as the ``RABBITMQ_USER`` / ``RABBITMQ_PASS`` pair.
        """
        host = os.environ.get("RABBITMQ_HOST", "rabbitmq")
        port = int(os.environ.get("RABBITMQ_PORT", "5672"))
        user = os.environ.get("RABBITMQ_USER", "guest")
        password = os.environ.get("RABBITMQ_PASS", "guest")
        return pika.ConnectionParameters(
            host=host,
            port=port,
            credentials=pika.PlainCredentials(user, password),
            heartbeat=60,
            connection_attempts=3,
            retry_delay=2,
            blocked_connection_timeout=30,
        )

    @api.model
    def _connect(self):
        """Open and return a ``pika.BlockingConnection``.

        :raises QueueUnavailable: pika missing (stale image), broker refused
            the connection (bad credentials, unreachable host, auth failure).
        """
        if not _PIKA_AVAILABLE:
            raise QueueUnavailable(
                _(
                    "pika is not installed in the running image. Rebuild the "
                    "odoo image so AMQP publishing works.",
                ),
            )
        try:
            return pika.BlockingConnection(self._connection_params())
        except pika.exceptions.AMQPConnectionError as exc:
            _logger.warning(
                "queue.publisher: cannot connect to RabbitMQ at %s:%s — %s",
                os.environ.get("RABBITMQ_HOST", "rabbitmq"),
                os.environ.get("RABBITMQ_PORT", "5672"),
                exc,
            )
            raise QueueUnavailable(str(exc)) from exc

    # ------------------------------------------------------------------
    # Publish API
    # ------------------------------------------------------------------
    @api.model
    def publish(self, routing_key, body, exchange=EXCHANGE_NAME):
        """Publish one JSON message to the invoice.agent exchange.

        The message is persistent (``delivery_mode=2``) so it survives a
        broker restart, and the body is JSON-serialized. The exchange and
        queues are declared by ``invoice_queue/topology.py`` — this method never
        declares anything, it only publishes (declaration belongs to the
        topology script / CI, not to a request-time code path).

        :param routing_key: ``extract.request`` or ``extract.done`` (the
            two bound keys; anything else is silently unroutable — a bug
            the management API's per-queue counts will reveal).
        :param body: dict or list — must be JSON-serializable.
        :param exchange: override the default exchange (tests use a
            throwaway exchange to prove messages never leave the test DB).
        :raises UserError: configuration error.
        :raises QueueUnavailable: broker unreachable or publish refused.
        """
        if not _PIKA_AVAILABLE:
            raise QueueUnavailable(
                _(
                    "pika is not installed in the running image. Rebuild the "
                    "odoo image so AMQP publishing works.",
                ),
            )
        payload = json.dumps(body, default=str)
        connection = self._connect()
        try:
            channel = connection.channel()
            channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=payload.encode("utf-8"),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # persistent message
                    content_type="application/json",
                ),
            )
            _logger.info(
                "queue.publisher: published %d bytes on %s/%s",
                len(payload),
                exchange,
                routing_key,
            )
        except pika.exceptions.AMQPError as exc:
            _logger.warning(
                "queue.publisher: publish failed on %s/%s — %s",
                exchange,
                routing_key,
                exc,
            )
            raise QueueUnavailable(str(exc)) from exc
        finally:
            try:
                connection.close()
            except Exception:
                _logger.exception("queue.publisher: error closing connection")

    @api.model
    def publish_extract_request(
        self,
        move_id,
        attachment_id=False,
        attempt=1,
        job_uuid=False,
        ocr_text=False,
    ):
        """Publish a durable ``extract.request`` job.

        Body contract (documented in ``invoice_queue/topology.py`` and
        ``docs/adr-004-rabbitmq.md``)::

            {"move_id": N, "attachment_id": M, "attempt": K,
             "job_uuid": "...", "ocr_text": "..."}

        ``move_id`` is the ``account.move`` queued for extraction,
        ``attachment_id`` is the source PDF (when known), ``attempt`` is the
        retry counter the worker reports back on ``extract.done``,
        ``job_uuid`` is the outbox correlation id the worker echoes back on
        ``extract.done`` (see ``account.move.ai_job_uuid``) and ``ocr_text``
        is the pre-OCR'd text the worker feeds to Claude (OCR runs Odoo-side
        via the ``_cron_ocr_pending_bills`` cron; the worker never touches
        PDFs).
        """
        rag_enabled = self.env["invoice.llm.service"].rag_enabled()
        return self.publish(
            ROUTING_KEY_REQUEST,
            {
                "move_id": int(move_id),
                "attachment_id": int(attachment_id) if attachment_id else False,
                "attempt": int(attempt),
                "job_uuid": job_uuid or "",
                "ocr_text": ocr_text or "",
                "rag_enabled": rag_enabled,
            },
        )

    @api.model
    def publish_embed_request(self, move_id, job_uuid=False, rag_text=False):
        """Publish a durable ``embed.request`` job for the RAG corpus.

        Body contract (documented in ``invoice_queue/topology.py`` and
        ``docs/vector-search.md``):::

            {"move_id": N, "job_uuid": "...", "rag_text": "..."}

        ``move_id`` is the posted ``account.move`` whose vendor-doc text the
        worker should embed, ``job_uuid`` is the outbox correlation id the
        worker echoes back on ``embed.done``, and ``rag_text`` is the
        rendered RAG document (``account.move._build_rag_document()``) the
        worker sends to ``/v1/embed``. The worker never touches the Odoo DB.
        """
        return self.publish(
            ROUTING_KEY_EMBED_REQUEST,
            {
                "move_id": int(move_id),
                "job_uuid": job_uuid or "",
                "rag_text": rag_text or "",
            },
        )
