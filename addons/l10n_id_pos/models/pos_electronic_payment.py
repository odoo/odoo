from odoo import models
from odoo.exceptions import UserError


class PosElectronicPayment(models.Model):
    _inherit = "pos.electronic.payment"

    def _get_bank_qr_code_context(self, extra_args: dict):
        if self.qr_code_method != "id_qr" or "order_uuid" not in extra_args:
            return super()._get_bank_qr_code_context(extra_args)

        return {
            **super()._get_bank_qr_code_context(extra_args),
            "qris_model": "pos.order",
            "qris_model_id": extra_args["order_uuid"],
        }

    def _get_transaction_status(self, transaction_id: str) -> dict:
        if self.payment_provider != "bank_qr" or self.qr_code_method != "id_qr":
            return super()._get_transaction_status(transaction_id)

        trx = self.env["l10n_id.qris.transaction"]._get_latest_transaction("pos.order", transaction_id)
        if not trx:
            raise UserError(self.env._("No QRIS transaction record is found based on this order"))

        result = trx._l10n_id_get_qris_qr_statuses()
        return {"status": "paid" if result["paid"] else "pending"}

    def _start_payment(self, amount: float, currency, extra_args: dict):
        if self.payment_provider != "bank_qr" or self.qr_code_method != "id_qr" or "order_uuid" not in extra_args:
            return super()._start_payment(amount, currency, extra_args)

        return {
            **super()._start_payment(amount, currency, extra_args),
            "transaction_id": extra_args["order_uuid"],
        }
