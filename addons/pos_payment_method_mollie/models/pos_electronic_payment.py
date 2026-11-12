from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import hash_sign

from odoo.addons.payment_mollie import const


class PosElectronicPayment(models.Model):
    _inherit = "pos.electronic.payment"

    mollie_terminal_id = fields.Char("Mollie Terminal ID", copy=False)
    mollie_payment_provider_id = fields.Many2one("payment.provider", domain=[("code", "=", "mollie")])
    mollie_api_key = fields.Char(related="mollie_payment_provider_id.mollie_api_key", related_sudo=False, groups="pos_payment_method.group_payment_method_admin")

    def _get_terminal_provider_selection(self):
        return super()._get_terminal_provider_selection() + [("mollie", "Mollie")]

    @api.onchange("mollie_api_key")
    def _onchange_mollie_api_key(self):
        for record in self:
            if record.mollie_payment_provider_id:
                record.mollie_payment_provider_id.mollie_api_key = record.mollie_api_key

    def _start_payment(self, amount: float, currency, extra_args: dict):
        if self.payment_provider != "mollie":
            return super()._start_payment(amount, currency, extra_args)

        if not self.sudo().mollie_payment_provider_id.mollie_api_key:
            raise ValidationError(self.env._("Please set the API key on the Mollie payment provider before making a payment."))

        user_lang = self.env.context.get("lang")
        payload = {
            "payment_method_id": self.id,
        }
        signed_payload = hash_sign(self.sudo().env, "pos_mollie", payload, expiration_hours=27)  # Mollie webhooks can retry for up to 26 hours
        payment_request = {
            "amount": {
                "currency": currency.name,
                "value": f"{amount:.{currency.decimal_places}f}",
            },
            "description": f"Odoo Payment Method: {self.name} (ID={self.id})",
            "locale": user_lang if user_lang in const.SUPPORTED_LOCALES else "en_US",
            "redirectUrl": f"{self.get_base_url()}",  # Not used for POS payments but required by Mollie API
            "webhookUrl": f"{self.get_base_url()}/pos_mollie/webhook?payload={signed_payload}",
            "method": "pointofsale",
            "terminalId": self.mollie_terminal_id,
        }

        mollie_response = self.sudo().mollie_payment_provider_id._send_api_request("POST", "/payments", json=payment_request)
        result = {"transaction_id": mollie_response["id"]}
        test_mode_payment_link = mollie_response.get("_links", {}).get("changePaymentState", {}).get("href")
        if test_mode_payment_link:
            result["mollie_test_mode_payment_link"] = test_mode_payment_link
        return result

    def _start_reversal(self, amount: float, currency, original_transaction_id: str, extra_args: dict):
        if self.payment_provider != "mollie":
            return super()._start_reversal(amount, currency, original_transaction_id, extra_args)

        payment_request = {
            "amount": {
                "currency": currency.name,
                "value": f"{amount:.{currency.decimal_places}f}",
            },
            "description": f"Odoo Payment Method: {self.name} (ID={self.id})",
        }
        mollie_response = self.sudo().mollie_payment_provider_id._send_api_request("POST", f"/payments/{original_transaction_id}/refunds", json=payment_request)

        return {"transaction_id": f"{original_transaction_id}/refunds/{mollie_response["id"]}"}

    def _cancel_transaction(self, transaction_id: str):
        if self.payment_provider != "mollie":
            return super()._cancel_transaction(transaction_id)

        self.sudo().mollie_payment_provider_id._send_api_request("DELETE", f"/payments/{transaction_id}")
        return {"transaction_id": transaction_id}

    def _get_transaction_status(self, transaction_id: str):
        if self.payment_provider != "mollie":
            return super()._get_transaction_status(transaction_id)

        mollie_response = self.sudo().mollie_payment_provider_id._send_api_request("GET", f"/payments/{transaction_id}")

        result = {
            "transaction_id": transaction_id,
            "status": self._mollie_status_to_odoo_status(mollie_response["status"]),
        }

        if mollie_response["status"] == "expired":
            result["error"] = self.env._("The payment has timed out.")
        elif mollie_response["status"] == "failed":
            result["error"] = mollie_response.get("statusReason", {}).get("message") or self.env._("The payment failed for an unknown reason.")

        if result["status"] == "paid" and "details" in mollie_response:
            result |= {
                "card_type": mollie_response["details"].get("cardFunding"),
                "card_no": mollie_response["details"].get("cardNumber"),
                "card_brand": mollie_response["details"].get("cardLabel"),
            }

        # When reversing a Mollie payment, it first stays in the 'pending' state for
        # around 10 minutes, before being confirmed. We don't want the cashier to be
        # blocked for 10 minutes waiting for the confirmation, so we will assume that
        # if the refund reaches this point it will be confirmed.
        if "/refunds/" in transaction_id and mollie_response["status"] == "pending":
            result["status"] = "paid"

        return result

    @api.model
    def _mollie_status_to_odoo_status(self, status: str):
        match status:
            case "paid" | "refunded":
                return "paid"
            case "failed" | "expired" | "canceled":
                return "failed"
            case _:
                return "pending"
