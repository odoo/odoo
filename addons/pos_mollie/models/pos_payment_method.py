import re

from odoo import Command, _, api, fields, models
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
    # Behaves like a related field, but the inverse is done in sudo as the provider API key is restricted to system users
    mollie_api_key = fields.Char(
        string="Mollie API Key",
        compute="_compute_mollie_api_key",
        inverse="_inverse_mollie_api_key",
        compute_sudo=True,
        groups="point_of_sale.group_pos_manager",
    )

    @api.depends("mollie_payment_provider_id.mollie_api_key")
    def _compute_mollie_api_key(self):
        for method in self:
            method.mollie_api_key = method.mollie_payment_provider_id.mollie_api_key

    def _inverse_mollie_api_key(self):
        for method in self:
            if method.mollie_payment_provider_id:
                method.mollie_payment_provider_id.sudo().mollie_api_key = method.mollie_api_key

    @api.onchange("mollie_payment_provider_id", "mollie_api_key")
    def _onchange_mollie_detect_terminal(self):
        """Prefill the terminal ID when exactly one active Mollie terminal is detected."""
        if (
            self.payment_provider != "mollie"
            or self.mollie_terminal_id
            or not self.mollie_payment_provider_id
            or not self.env.user.has_group("point_of_sale.group_pos_manager")
        ):
            return
        try:
            terminals = self._mollie_fetch_active_terminals()
        except ValidationError:
            # The user can still use the 'Connect Terminal' button or fill the terminal ID manually
            return
        if len(terminals) == 1:
            self.mollie_terminal_id = terminals[0]["id"]

    def _mollie_fetch_active_terminals(self):
        """Return the active terminals of the Mollie account linked to the payment provider.

        :return: The terminals, as returned by the Mollie API.
        :rtype: list[dict]
        :raise ValidationError: If the API key is missing or the request fails.
        """
        provider = self.sudo().mollie_payment_provider_id._origin
        # Value from the form, which may not be saved on the provider yet
        api_key = self.sudo().mollie_api_key
        if not provider or not api_key:
            raise ValidationError(_("Please set the API key on the Mollie payment provider first."))
        if api_key != provider.mollie_api_key:
            # Unsaved copy of the provider carrying the API key typed in the form
            provider = provider.new({"mollie_api_key": api_key}, origin=provider)
        response = provider._send_api_request("GET", "/terminals", params={"limit": 20})
        terminals = (response.get("_embedded") or {}).get("terminals") or []
        return [terminal for terminal in terminals if terminal.get("status") == "active"]

    def _mollie_display_notification(self, level, message, reload=False):
        params = {
            "type": level,
            "message": message,
        }
        if reload:
            # Reload the record to show the updated terminal ID
            params["next"] = {"type": "ir.actions.client", "tag": "soft_reload"}
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": params,
        }

    def action_mollie_connect_terminal(self):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group("point_of_sale.group_pos_manager"):
            raise AccessError(_("You do not have the necessary permissions to connect a Mollie terminal."))
        try:
            terminals = self._mollie_fetch_active_terminals()
        except ValidationError as e:
            return self._mollie_display_notification("danger", _("Failed to retrieve the Mollie terminals: %s", e))
        if not terminals:
            return self._mollie_display_notification("danger", _("No active Mollie terminal found. Please make sure the terminal is activated in your Mollie account."))
        # If only 1 terminal is found, set it as the current terminal
        if len(terminals) == 1:
            terminal_id = terminals[0]["id"]
            if self.mollie_terminal_id == terminal_id:
                return self._mollie_display_notification("warning", _("Detected Mollie terminal %s is already set as the current terminal.", terminal_id), reload=True)
            self.mollie_terminal_id = terminal_id
            return self._mollie_display_notification("success", _("Found Mollie terminal %s and set it as the current terminal.", terminal_id), reload=True)
        # If multiple terminals are found, let the user choose which one to connect
        wizard = self.env["pos.mollie.terminal.wizard"].create({
            "payment_method_id": self.id,
            "line_ids": [Command.create({
                "name": terminal["id"],
                "description": terminal.get("description"),
                "serial_number": terminal.get("serialNumber"),
            }) for terminal in terminals],
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("Multiple Mollie terminals found"),
            "res_model": "pos.mollie.terminal.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
        }

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
        if not self.mollie_terminal_id:
            raise ValidationError(_("Please set the Mollie terminal ID on the payment method before making a payment."))

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
