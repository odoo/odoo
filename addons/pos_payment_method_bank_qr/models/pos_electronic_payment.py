from uuid import uuid4

from odoo import fields, models


class PosElectronicPayment(models.Model):
    _inherit = "pos.electronic.payment"

    bank_account_id = fields.Many2one("res.partner.bank", domain=[("journal_id", "!=", False)])
    qr_code_method = fields.Selection(
        string="QR Code Format",
        selection=lambda self: self.env["res.partner.bank"].get_available_qr_methods_in_sequence(),
        help="Type of QR-code to be generated.",
    )

    def _get_qr_provider_selection(self):
        return super()._get_qr_provider_selection() + [("bank_qr", "Bank QR code")]

    def _is_supported_in_kiosk(self):
        if self.payment_provider != "bank_qr":
            return super()._is_supported_in_kiosk()

        return self.qr_code_method == "id_qr"

    def _get_bank_qr_code_context(self, extra_args: dict):
        return {
            "is_online_qr": True,
        }

    def _init_payment_method(self):
        if self.payment_provider != "bank_qr":
            return super()._init_payment_method()

        return {
            "qr_code_method": self.qr_code_method,
        }

    def _start_payment(self, amount: float, currency, extra_args: dict):
        if self.payment_provider != "bank_qr":
            return super()._start_payment(amount, currency, extra_args)

        order_number = extra_args.get("order_number", "")
        if order_number:
            order_number = self.env._("Order #%s", order_number)
        partner = self.env["res.partner"].browse(extra_args.get("partner_id"))

        qr_code_text = self.bank_account_id.with_context(
            **self._get_bank_qr_code_context(extra_args),
        ).build_qr_code_value(
            amount,
            order_number,
            "",
            currency,
            partner,
            self.qr_code_method,
            silent_errors=False,
        )

        return {"qr_code": qr_code_text, "transaction_id": uuid4().hex}
