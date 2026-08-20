import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

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
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    # v0.10: job kind distinguishes AMQP message types sharing the outbox.
    # "extract" publishes extract.request for the AI worker; "embed"
    # publishes an embed.request job that the worker answers by calling
    # /v1/embed and publishing a signed embed.done result — posting a bill
    # only enqueues (never blocks on the embed HTTP round-trip).
    kind = fields.Selection(
        selection=[
            ("extract", "Extract"),
            ("embed", "Embed"),
        ],
        string="Kind",
        default="extract",
        required=True,
        index=True,
        copy=False,
        help="extract: Claude extraction job (extract.request). embed: "
        "RAG vendor-doc embedding job (embed.request).",
    )
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Source Attachment",
        ondelete="set null",
        help="The source PDF/image the worker should OCR + extract.",
    )
    # v0.9: the correlation id is persisted on the outbox row itself (mirrors
    # account.move.ai_job_uuid) so the dead-letter taskboard can correlate a
    # poison message back to the exact outbox row. UNIQUE — see
    # _sql_constraints — enforces the same job is never published twice.
    job_uuid = fields.Char(
        string="Job UUID",
        index=True,
        readonly=True,
        copy=False,
        help="UUID correlating this outbox row with the AMQP job message. "
        "Unique per job: a redelivered message is a no-op.",
    )
    state = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("sent", "Sent"),
            ("dead", "Dead-Lettered"),
        ],
        string="State",
        default="pending",
        required=True,
        index=True,
        help="pending: not yet published to the broker. sent: published, "
        "published_at stamped. dead: the worker dead-lettered this job "
        "(poison message) — requeue to retry.",
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
    # v0.9 dead-letter visibility: why the worker poisoned the job, and how
    # many delivery attempts the broker counted (x-death count).
    dead_reason = fields.Text(
        string="Dead-Letter Reason",
        readonly=True,
        help="Why the worker dead-lettered this job (x-death-reason).",
    )
    x_death_count = fields.Integer(
        string="x-death Count",
        readonly=True,
        default=0,
        help="Number of dead-letter hops the broker stamped for this job.",
    )

    _sql_constraints = [
        (
            "job_uuid_unique",
            "UNIQUE(job_uuid)",
            (
                "Each extraction job must have a unique job_uuid — a redelivered "
                "message must never create a second outbox row."
            ),
        ),
    ]

    # ------------------------------------------------------------------
    # Drain API — called by ir.cron every minute
    # ------------------------------------------------------------------
    @api.model
    def _drain_pending(self, limit=50):
        """Publish unsent outbox rows to ``extract.request`` and stamp them.

        Batch-bounded (``limit``) and per-row isolated using savepoints.
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
            # Per-row isolation: a failed publish marks only this row and
            # never rolls back the rest of the batch.
            try:
                with self.env.cr.savepoint():
                    # job_uuid source of truth: the outbox row. Falls back to
                    # the move's ai_job_uuid for rows created before v0.9.
                    job_uuid = job.job_uuid or job.move_id.ai_job_uuid
                    if not job_uuid:
                        # Backfill from the move (pre-v0.9 rows) atomically.
                        job.write({"job_uuid": job.move_id.ai_job_uuid})
                        job_uuid = job.job_uuid
                    publisher = self.env["queue.publisher"]
                    if job.kind == "embed":
                        # v0.10: RAG embed job. Executed by the drain cron
                        # (not a broker round-trip): the posting request only
                        # enqueues this outbox row — the embed HTTP call runs
                        # on the cron's clock, so posting a bill never blocks.
                        # embed_texts() returns None on 503/connection errors;
                        # the row stays pending and the next drain retries.
                        rag_text = job.move_id._build_rag_document()
                        vectors = self.env["invoice.llm.service"].embed_texts(
                            [rag_text],
                        )
                        if vectors:
                            self.env["invoice.agent.vendor.doc"].upsert_embedding(
                                job.move_id.id,
                                rag_text,
                                vectors[0],
                            )
                            job.move_id.write({"ai_indexed": True})
                        else:
                            # Deferred — keep pending so the next tick retries.
                            # The savepoint rolls back; the row stays state=
                            # "pending" with no state="sent" write.
                            continue
                    else:
                        # Job payload: move_id + attachment_id + attempt plus
                        # the correlation id (job_uuid) and the OCR text the
                        # worker feeds to Claude. OCR runs Odoo-side (cron),
                        # so the worker never touches PDFs.
                        publisher.publish_extract_request(
                            job.move_id.id,
                            attachment_id=(
                                job.attachment_id.id if job.attachment_id else False
                            ),
                            job_uuid=job_uuid,
                            ocr_text=job.move_id.ocr_text or job.move_id.ai_ocr_text,
                        )
                    job.write(
                        {
                            "state": "sent",
                            "published_at": fields.Datetime.now(),
                            "error_message": False,
                        }
                    )
                    # Live UI update: the job reached the broker — notify the
                    # move's followers so the Owl status widget flips to
                    # "queued" without a page refresh. Best-effort: a bus
                    # failure must never break the drain.
                    try:
                        from odoo.addons.invoice_agent.models.queue_consumer import (
                            _publish_live_status,
                        )

                        move = job.move_id
                        if move:
                            _publish_live_status(move, "queued", {"job_id": job.id})
                    except Exception:
                        _logger.exception(
                            "invoice_agent failed to publish queued status for "
                            "move_id=%s",
                            job.move_id.id,
                        )
                    sent += 1
            except QueueUnavailable as exc:
                # Broker unavailable: record the error and leave the row
                # unsent; the next cron tick retries it.
                job.write({"error_message": str(exc)[:2000]})
                _logger.warning(
                    "outbox drain: broker unavailable, job %d stays pending: %s",
                    job.id,
                    exc,
                )
            except Exception as exc:
                # Any other error: log and record, protect the next cycle.
                _logger.exception("outbox drain: unexpected failure on job %d", job.id)
                job.write({"error_message": str(exc)[:2000]})

        return sent

    @api.model
    def _cron_drain_outbox(self, batch_size=50):
        """ir.cron entry point — drain with a per-batch commit window."""
        return self._drain_pending(limit=batch_size)

    # ------------------------------------------------------------------
    # v0.9: dead-letter taskboard helpers
    # ------------------------------------------------------------------
    @api.model
    def _mark_dead(self, job_uuid, reason="", x_death_count=0):
        """Mark the outbox row for ``job_uuid`` as dead-lettered.

        Called by the result consumer when a signed ``status:"failed"``
        result arrives (the worker dead-lettered the poison message). No-op
        when no row matches — the consumer never raises on missing rows.
        """
        job = self.search([("job_uuid", "=", job_uuid)], limit=1)
        if not job:
            _logger.warning(
                "invoice_agent: no outbox row for dead-letter job_uuid=%s",
                job_uuid,
            )
            return False
        job.write(
            {
                "state": "dead",
                "dead_reason": (reason or "")[:2000],
                "x_death_count": max(int(x_death_count or 0), job.x_death_count or 0),
            }
        )
        _logger.info(
            "invoice_agent: job %d dead-lettered (uuid=%s): %s",
            job.id,
            job_uuid,
            (reason or "")[:200],
        )
        return True

    def action_requeue(self):
        """Requeue a dead-lettered job back to the pending drain.

        Resets the row to pending so the drain cron republishes it to
        ``extract.request``. Idempotency is guaranteed by the UNIQUE
        ``job_uuid``: the move keeps its ai_job_uuid, so a redelivered
        result can never create a second draft.
        """
        for job in self:
            if job.state != "dead":
                raise UserError(
                    _("Only dead-lettered jobs can be requeued (job %s).", job.id)
                )
            job.write(
                {
                    "state": "pending",
                    "dead_reason": False,
                    "x_death_count": 0,
                    "error_message": False,
                }
            )
            # The move's extraction state must be retryable again.
            move = job.move_id
            if move:
                move.write({"ai_extraction_status": "pending"})
            _logger.info(
                "invoice_agent: requeued dead job %d (uuid=%s)",
                job.id,
                job.job_uuid,
            )
        return True
