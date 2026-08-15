"""Transactional outbox for AMQP extraction jobs (``invoice.agent.job``).

Why an outbox at all — the core argument of ``docs/adr-004-rabbitmq.md``:

AMQP 0-9-1 has no transaction spanning the broker and the database. If the
``account.move`` write publishes directly to RabbitMQ and the surrounding
Odoo transaction later rolls back (constraint violation, an exception caught
by the caller, a pre-commit hook), the message is already on the broker — an
*orphan job* with a ``move_id`` pointing at a bill that does not exist. The
worker consumes it and either crashes or fabricates state for a phantom
record.

The outbox pattern closes exactly that gap:

1. The publisher writes a row on **the same cursor** as the ``account.move``
   write. Both commit or both roll back atomically. If the move write rolls
   back, the outbox row rolls back with it — nothing ever reaches the
   broker. If the move commits, the outbox row is durable and *exactly once
   unsent*.
2. A dedicated ``ir.cron`` drains the outbox every minute: it picks unsent
   rows, publishes ``extract.request`` and stamps ``published_at``. The
   row->queue handoff is safe against crashes because ``published_at`` is
   written on the same transaction as the publish has *not* completed.
3. Because the publish happens in a *separate* transaction from the user's
   write, a broker outage or slow network cannot delay the user's save. The
   cron retries unsent rows until the broker is back.

State machine: ``pending -> sent`` (+ ``published_at`` timestamp; failed
publishes leave the row ``pending`` with ``error_message`` set so the cron
retries it).

Forced-rollback tests (``tests/test_queue_publisher.py``) prove the
invariant: a transaction that rolls back after ``action_request_ai_extraction``
leaves zero outbox rows and zero broker messages.
"""

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class InvoiceAgentJob(models.Model):
    _name = "invoice.agent.job"
    _description = "Transactional outbox row for AMQP extraction jobs"
    _order = "create_date asc, id asc"

    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Invoice",
        required=True,
        ondelete="cascade",
        index=True,
        help="The account.move whose extraction this job publishes for.",
    )
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Source Attachment",
        ondelete="set null",
        help="The source PDF/image the worker should OCR + extract.",
    )
    state = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("sent", "Sent"),
        ],
        string="State",
        default="pending",
        required=True,
        index=True,
        help="pending: not yet published to the broker. sent: published, "
        "published_at stamped.",
    )
    published_at = fields.Datetime(
        string="Published At",
        readonly=True,
        index=True,
        help="When the drain cron successfully published the extract.request "
        "message for this row.",
    )
    error_message = fields.Text(
        string="Error Message",
        readonly=True,
        help="Last publish failure reason. Kept so the ops queue can see why "
        "a job is stuck pending without grepping logs.",
    )

    # ------------------------------------------------------------------
    # Drain API — called by ir.cron every minute
    # ------------------------------------------------------------------
    @api.model
    def _drain_pending(self, limit=50):
        """Publish unsent outbox rows to ``extract.request`` and stamp them.

        Batch-bounded (``limit``) and per-row isolated: one broker failure
        marks that row with ``error_message`` but never blocks the rest of
        the batch. Rows are claimed oldest-first (FIFO).
        """
        from odoo.addons.invoice_agent.models.queue_publisher import (
            QueueUnavailable,
        )

        jobs = self.search(
            [("state", "=", "pending")],
            order="create_date asc, id asc",
            limit=limit,
        )
        sent = 0
        for job in jobs:
            try:
                self.env["queue.publisher"].publish_extract_request(
                    job.move_id.id,
                    attachment_id=job.attachment_id.id if job.attachment_id else False,
                )
                job.write(
                    {
                        "state": "sent",
                        "published_at": fields.Datetime.now(),
                        "error_message": False,
                    },
                )
                sent += 1
            except QueueUnavailable as exc:
                # Broker down — leave the row pending for the next tick.
                job.write({"error_message": str(exc)[:2000]})
                _logger.warning(
                    "outbox drain: broker unavailable, job %d stays pending: %s",
                    job.id,
                    exc,
                )
            except Exception as exc:
                _logger.exception("outbox drain: unexpected failure on job %d", job.id)
                job.write({"error_message": str(exc)[:2000]})
        return sent

    @api.model
    def _cron_drain_outbox(self, batch_size=50):
        """ir.cron entry point — drain with a per-batch commit window.

        The cron runs its own transaction; publishing happens per row but the
        whole batch commits at the end (cron code runs inside one transaction
        unless we commit explicitly). A single failed row is caught above, so
        this method itself never raises.
        """
        return self._drain_pending(limit=batch_size)
