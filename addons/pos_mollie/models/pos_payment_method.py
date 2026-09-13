from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import hash_sign

from odoo.addons.payment_mollie import const


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def _selection_payment_terminals(self):
        return super()._selection_payment_terminals() + [("mollie", "Mollie")]

    mollie_terminal_id = fields.Char(
        string="Mollie Terminal ID",
        copy=False,
    )
    mollie_payment_provider_id = fields.Many2one(
        comodel_name="payment.provider",
        domain=[("code", "=", "mollie")],
    )

    @api.constrains("mollie_payment_provider_id")
    def _check_mollie_payment_provider_id(self):
        for payment_method in self:
            if not payment_method.mollie_payment_provider_id:
                continue
            if not payment_method.mollie_payment_provider_id.mollie_api_key:
                raise ValidationError(
                    _(
                        "Please set the Mollie API Key field on the %s payment provider.",
                        payment_method.mollie_payment_provider_id.name,
                    )
                )

    def mollie_create_payment(
        self, amount: float, payment_uuid: str, pos_session_id: int
    ):
        self.check_singleton()

        user_lang = self.env.context.get("lang")
        currency = self.journal_id.currency_id or self.company_id.currency_id
        payload = {
            "payment_uuid": payment_uuid,
            "payment_method_id": self.id,
            "pos_session_id": pos_session_id,
        }
        signed_payload = hash_sign(
            self.sudo().env, "pos_mollie", payload, expiration_hours=27
        )  # Mollie webhooks can retry for up to 26 hours
        payment_request = {
            "amount": {
                "currency": currency.name,
                "value": f"{amount:.{currency.decimal_places}f}",
            },
            "locale": user_lang if user_lang in const.SUPPORTED_LOCALES else "en_US",
            "description": f"pos_session_id={pos_session_id},payment_uuid={payment_uuid}",
            "redirectUrl": f"{self.get_base_url()}",  # Not used for POS payments but required by Mollie API
            "webhookUrl": f"{self.get_base_url()}/pos_mollie/webhook?payload={signed_payload}",
            "method": "pointofsale",
            "terminalId": self.mollie_terminal_id,
        }
        return self.mollie_payment_provider_id._send_api_request(
            "POST", "/payments", json=payment_request
        )

    def mollie_create_refund(
        self,
        original_payment_id: str,
        amount: float,
        payment_uuid: str,
        pos_session_id: int,
    ):
        self.check_singleton()

        currency = self.journal_id.currency_id or self.company_id.currency_id
        payment_request = {
            "amount": {
                "currency": currency.name,
                "value": f"{amount:.{currency.decimal_places}f}",
            },
            "description": f"pos_session_id={pos_session_id},payment_uuid={payment_uuid}",
        }
        return self.mollie_payment_provider_id._send_api_request(
            "POST", f"/payments/{original_payment_id}/refunds", json=payment_request
        )

    def mollie_cancel_payment(self, payment_id: str):
        self.check_singleton()
        return self.mollie_payment_provider_id._send_api_request(
            "DELETE", f"/payments/{payment_id}"
        )

    def _mollie_get_payment(self, payment_id: str):
        self.check_singleton()
        return self.mollie_payment_provider_id._send_api_request(
            "GET", f"/payments/{payment_id}"
        )
