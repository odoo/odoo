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
                    # Job payload: move_id + attachment_id + attempt plus the
                    # correlation id (job_uuid) and the OCR text the worker
                    # feeds to Claude. OCR runs Odoo-side (cron), so the
                    # worker never touches PDFs.
                    self.env["queue.publisher"].publish_extract_request(
                        job.move_id.id,
                        attachment_id=(
                            job.attachment_id.id if job.attachment_id else False
                        ),
                        job_uuid=job.move_id.ai_job_uuid,
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
