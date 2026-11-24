from datetime import timedelta

from odoo import fields, models
from odoo.exceptions import UserError

KIOSK_QRIS_TIMEOUT = 180

# Reusing the QR already on screen spares the acquirer a second code on a double tap.
# The margin keeps the reuse below `KIOSK_QRIS_TIMEOUT`, past which the backend calls
# the transaction expired, and leaves a retry enough time to actually be paid.
KIOSK_QRIS_REUSE_WINDOW = KIOSK_QRIS_TIMEOUT - 30


class PosElectronicPayment(models.Model):
    _inherit = "pos.electronic.payment"

    def _qris_kiosk_qr_transactions(self, order_uuid: str, amount: float):
        """
        The QRs issued for ``order_uuid`` that can still pay it, newest first.

        All of them are relevant, not only the one the kiosk currently displays: QRIS has
        no way to invalidate a QR, so every code handed out for this order stays payable
        for the 30 minutes the acquirer keeps it, well past the kiosk countdown. QRs for
        another amount are left out, they do not pay this order.
        """
        return self.env["l10n_id.qris.transaction"].sudo().search([
            ("model", "=", "pos.order"),
            ("model_id", "=", order_uuid),
            ("qris_amount", "=", int(amount)),
        ], order="qris_creation_datetime desc")

    def _qris_kiosk_qr_expires_in(self, order_uuid: str, amount: float):
        """
        Seconds left before the QR of ``order_uuid`` expires, counted from when the acquirer
        created it rather than from now: a reused QR is already partway through its life,
        and the kiosk countdown has to show the time that is actually left.
        """
        transactions = self._qris_kiosk_qr_transactions(order_uuid, amount)
        if not transactions:
            return KIOSK_QRIS_TIMEOUT
        age = (fields.Datetime.now() - transactions[0].qris_creation_datetime).total_seconds()
        return max(0, KIOSK_QRIS_TIMEOUT - int(age))

    def _qris_kiosk_qr_fetch_status(self, order):
        """
        Return the current QRIS payment status, considering every QR issued for ``order``.

        :param order: the ``pos.order`` being paid
        :return: ``'pending'``, ``'paid'`` or ``'failed'``
        :rtype: str
        """
        transactions = self._qris_kiosk_qr_transactions(order.uuid, order.amount_total)
        if not transactions:
            return "failed"
        if any(transactions.mapped("paid")):
            return "paid"

        if transactions._l10n_id_get_qris_qr_statuses()["paid"]:
            return "paid"

        age = fields.Datetime.now() - transactions[0].qris_creation_datetime
        if age > timedelta(seconds=KIOSK_QRIS_TIMEOUT):
            return "failed"
        return "pending"

    def _get_bank_qr_code_context(self, extra_args: dict):
        if self.qr_code_method != "id_qr" or "kiosk_order_id" not in extra_args:
            return super()._get_bank_qr_code_context(extra_args)

        return {
            **super()._get_bank_qr_code_context(extra_args),
            "qris_max_reuse_seconds": KIOSK_QRIS_REUSE_WINDOW,
        }

    def _get_bank_qr_status(self, transaction_id: str) -> dict:
        if self.qr_code_method != "id_qr":
            return super()._get_bank_qr_status(transaction_id)
        payment = self._kiosk_get_pending_payment(transaction_id)
        if not payment:
            return super()._get_bank_qr_status(transaction_id)

        return {"status": self._qris_kiosk_qr_fetch_status(payment.pos_order_id)}

    def _start_payment(self, amount: float, currency, extra_args: dict):
        if self.payment_provider != "bank_qr" or self.qr_code_method != "id_qr" or "order_uuid" not in extra_args or "kiosk_order_id" not in extra_args:
            return super()._start_payment(amount, currency, extra_args)

        try:
            previous_payment = self.get_transaction_status(extra_args["order_uuid"])
            if previous_payment["status"] == "paid":
                return previous_payment
        except UserError:
            pass

        return {
            **super()._start_payment(amount, currency, extra_args),
            "expires_in": self._qris_kiosk_qr_expires_in(extra_args["order_uuid"], amount),
        }
