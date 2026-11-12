from odoo import fields, models


class PosElectronicPayment(models.Model):
    _inherit = "pos.electronic.payment"

    bank_journal_id = fields.Many2one("account.journal", domain=[("type", "=", "bank")], required=True)
    qr_code_method = fields.Selection(
        string='QR Code Format',
        required=True,
        selection=lambda self: self.env['res.partner.bank'].get_available_qr_methods_in_sequence(),
        help='Type of QR-code to be generated.',
    )

    def _get_qr_provider_selection(self):
        return super()._get_qr_provider_selection() + [("bank_qr", "Bank QR code")]

    def _start_payment(self, amount: float, currency, extra_args: dict):
        if self.payment_provider != "bank_qr":
            return super()._start_payment(amount, currency, extra_args)

        partner = self.env["res.partner"].browse(extra_args.get("partner_id"))
        order_number = extra_args.get("order_number", "")
        if order_number:
            order_number = self.env._("Order #%s", order_number)
        return {"qr_code": self._get_bank_qr_code_value(amount, order_number, "", currency, partner)}

    def _get_bank_qr_code_value(self, amount: float, free_communication: str, structured_communication: str, currency, debtor_partner):
        """ Returns the payment payload to encode in the QR-code.

        The QR-code image itself is drawn by the POS client, so this must be the
        raw value the bank application expects (e.g. the EMV string), not the URL
        of a report rendering it.
        """
        payment_bank = self.bank_journal_id.bank_account_id

        return payment_bank.with_context(is_online_qr=True).build_qr_code_value(
            float(amount), free_communication, structured_communication, currency, debtor_partner, self.qr_code_method, silent_errors=False)
