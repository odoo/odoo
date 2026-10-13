import re

from odoo import _, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import hash_sign

from odoo.addons.payment_mollie import const


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def _get_terminal_provider_selection(self):
        return super()._get_terminal_provider_selection() + [("mollie", "Mollie")]

    def _allowed_actions_in_self_order(self):
        return super()._allowed_actions_in_self_order() + ["mollie_create_payment", "mollie_cancel_payment", "mollie_get_payment"]

    mollie_terminal_id = fields.Char("Mollie Terminal ID", copy=False)
    mollie_payment_provider_id = fields.Many2one("payment.provider", domain=[("code", "=", "mollie")])

    def _check_mollie_access(self, pos_session_id=None, payment_id=None):
        if not self.env.su and not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(_("You do not have the necessary permissions to access this payment."))
        if payment_id is not None and not re.fullmatch(r"tr_.+", payment_id):
            raise ValidationError(_("Invalid Mollie payment ID."))
        if pos_session_id is not None:
            pos_session = self.env["pos.session"].browse(pos_session_id).exists()
            if not pos_session or pos_session.state == "closed" or self not in pos_session.config_id.payment_method_ids:
                raise ValidationError(_("This payment method is not available in an open session of this Point of Sale."))

    def mollie_create_payment(self, amount: float, payment_uuid: str, pos_session_id: int):
        self.ensure_one()
        self._check_mollie_access(pos_session_id)

        if not self.sudo().mollie_payment_provider_id.mollie_api_key:
            raise ValidationError(_("Please set the API key on the Mollie payment provider before making a payment."))

        user_lang = self.env.context.get("lang")
        currency = self.journal_id.currency_id or self.company_id.currency_id
        payload = {
            "payment_uuid": payment_uuid,
            "payment_method_id": self.id,
            "pos_session_id": pos_session_id,
        }
        signed_payload = hash_sign(self.sudo().env, "pos_mollie", payload, expiration_hours=27)  # Mollie webhooks can retry for up to 26 hours
        payment_request = {
            "amount": {
                "currency": currency.name,
                "value": f"{amount:.{currency.decimal_places}f}"
            },
            "locale": user_lang if user_lang in const.SUPPORTED_LOCALES else "en_US",
            "description": f"pos_session_id={pos_session_id},payment_uuid={payment_uuid}",
            "redirectUrl": f"{self.get_base_url()}",  # Not used for POS payments but required by Mollie API
            "webhookUrl": f"{self.get_base_url()}/pos_mollie/webhook?payload={signed_payload}",
            "method": "pointofsale",
            "terminalId": self.mollie_terminal_id,
            "metadata": payload,
        }
        response = self.sudo().mollie_payment_provider_id._send_api_request("POST", "/payments", json=payment_request)
        return self._parse_mollie_payment(response)

    def mollie_create_refund(self, original_payment_id: str, amount: float, payment_uuid: str, pos_session_id: int):
        self.ensure_one()
        self._check_mollie_access(pos_session_id, original_payment_id)
        self._fetch_mollie_payment(original_payment_id)

        currency = self.journal_id.currency_id or self.company_id.currency_id
        payment_request = {
            "amount": {
                "currency": currency.name,
                "value": f"{amount:.{currency.decimal_places}f}"
            },
            "description": f"pos_session_id={pos_session_id},payment_uuid={payment_uuid}",
        }
        response = self.sudo().mollie_payment_provider_id._send_api_request("POST", f"/payments/{original_payment_id}/refunds", json=payment_request)
        return self._parse_mollie_payment(response)

    def mollie_cancel_payment(self, payment_id: str, pos_session_id: int):
        self.ensure_one()
        self._check_mollie_access(pos_session_id, payment_id)
        self._fetch_mollie_payment(payment_id, pos_session_id)
        response = self.sudo().mollie_payment_provider_id._send_api_request("DELETE", f"/payments/{payment_id}")
        return self._parse_mollie_payment(response)

    def mollie_get_payment(self, payment_id: str, pos_session_id: int, payment_uuid: str | None = None):
        self.ensure_one()
        self._check_mollie_access(pos_session_id, payment_id)
        response = self._fetch_mollie_payment(payment_id, pos_session_id, payment_uuid)
        return self._parse_mollie_payment(response)

    def _fetch_mollie_payment(self, payment_id, pos_session_id=None, payment_uuid=None):
        response = self.sudo().mollie_payment_provider_id._send_api_request("GET", f"/payments/{payment_id}")
        self._check_mollie_metadata(response, pos_session_id, payment_uuid)
        return response

    def _check_mollie_metadata(self, payment_info, pos_session_id=None, payment_uuid=None):
        metadata = payment_info.get("metadata")
        if (
            not isinstance(metadata, dict)
            or metadata.get("payment_method_id") != self.id
            or (pos_session_id is not None and metadata.get("pos_session_id") != pos_session_id)
            or (payment_uuid is not None and metadata.get("payment_uuid") != payment_uuid)
        ):
            raise ValidationError(_("This Mollie payment does not belong to this Point of Sale."))

    def _parse_mollie_payment(self, payment_info):
        def _get_dict(data, *keys):
            *path, last_key = keys
            for key in path:
                data = data.get(key) or {}
            return data.get(last_key)

        result = {
            'payment_id': payment_info["id"],
            'status': payment_info["status"],
            # Only set in test mode, to simulate the terminal
            'test_terminal_url': _get_dict(payment_info, "_links", "changePaymentState", "href"),
        }
        if result['status'] == "paid":
            result |= {
                'card_type': _get_dict(payment_info, "details", "cardFunding"),
                'card_no': _get_dict(payment_info, "details", "cardNumber"),
                'card_brand': _get_dict(payment_info, "details", "cardLabel"),
            }
        elif result['status'] in ['expired', 'failed', 'canceled']:
            result |= {
                'status_reason': payment_info.get("statusReason"),
            }
        return result
