# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import traceback

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools.sql import create_index, make_index_name

_logger = logging.getLogger(__name__)


class PaymentData(models.Model):
    _name = "payment.data"
    _description = "Pending payment data payload to process"

    def _auto_init(self):
        """Create a partial index to speed up the search of non-errored records."""
        super()._auto_init()
        create_index(
            self.env.cr,
            make_index_name(self._table, "errored"),
            self._table,
            ["id"],
            where="errored IS NOT TRUE",
        )

    transaction_id = fields.Many2one(
        string="Transaction",
        comodel_name="payment.transaction",
        ondelete="restrict",
        required=True,
        index=True,
    )
    payload = fields.Json(string="Payload", required=True)
    errored = fields.Boolean(string="Failed")
    error_traceback = fields.Text(string="Error Traceback")

    @api.model
    def _cron_process(self):
        """Run the processing of pending payment data.

        Payment data records are processed in insertion order to ensure that older transactions are
        handled first and that same-transaction operations are applied in the correct sequence.

        After successful processing, payment data records are deleted. If it fails, they are marked
        as errored and left for manual intervention.

        :rtype: None
        """
        # Keep fetching pending payment data until all remaining records have been processed
        IrCron = self.env["ir.cron"]
        while pending_payment_data := self.env["payment.data"].search(
            Domain("errored", "=", False), limit=1000
        ):
            # Update the remaining count after each fetch to keep the cron running
            IrCron._commit_progress(remaining=len(pending_payment_data))

            for payment_data in pending_payment_data:
                # Lock the current records to prevent concurrent processing and restrict prefetching
                tx = payment_data.transaction_id.try_lock_for_update()
                payment_data = payment_data.try_lock_for_update()
                if not tx or not payment_data:  # The lock could not be acquired
                    IrCron._rollback_progress()  # Release the lock on whichever record was locked
                    continue  # Skip for now; will be retried on the next run

                try:
                    # Process the payment data
                    tx.with_context(
                        # Relevant records have been locked above; no concurrent write is possible
                        payment_safe_write=True
                    )._process(payment_data.payload)
                    payment_data.unlink()

                    # Commit the progress and get the remaining time
                    remaining_time = IrCron._commit_progress(processed=1)
                except Exception:
                    IrCron._rollback_progress()
                    payment_data.write({"errored": True, "error_traceback": traceback.format_exc()})
                    _logger.exception(
                        "Failed to process payment data %s for transaction %s.",
                        payment_data.id,
                        tx.reference,
                    )
                    # Commit the progress and get the remaining time
                    remaining_time = IrCron._commit_progress(processed=1)

                if not remaining_time:  # The cron job might be killed soon
                    return
