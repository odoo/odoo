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
            # استخدام savepoint لعزل كل سجل بشكل مستقل ومنع إلغاء الدفعة كاملاً عند حدوث خطأ
            try:
                with self.env.cr.savepoint():
                    self.env["queue.publisher"].publish_extract_request(
                        job.move_id.id,
                        attachment_id=(
                            job.attachment_id.id if job.attachment_id else False
                        ),
                    )
                    job.write(
                        {
                            "state": "sent",
                            "published_at": fields.Datetime.now(),
                            "error_message": False,
                        }
                    )
                    sent += 1
            except QueueUnavailable as exc:
                # خطأ في الوسيط: نحدث السجل برسالة الخطأ دون إيقاف باقي الدفعة
                job.write({"error_message": str(exc)[:2000]})
                _logger.warning(
                    "outbox drain: broker unavailable, job %d stays pending: %s",
                    job.id,
                    exc,
                )
            except Exception as exc:
                # أي خطأ آخر يتم تسجيله وتحديث السجل لحماية الدورة القادمة
                _logger.exception("outbox drain: unexpected failure on job %d", job.id)
                job.write({"error_message": str(exc)[:2000]})

        return sent

    @api.model
    def _cron_drain_outbox(self, batch_size=50):
        """ir.cron entry point — drain with a per-batch commit window."""
        return self._drain_pending(limit=batch_size)
