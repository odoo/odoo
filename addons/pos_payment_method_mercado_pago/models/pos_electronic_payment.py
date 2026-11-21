import logging
from uuid import uuid4

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_repr

from .mercado_pago_pos_request import MERCADO_PAGO_PLATFORM_ID, MercadoPagoPosRequest

_logger = logging.getLogger(__name__)


class PosElectronicPayment(models.Model):
    _inherit = "pos.electronic.payment"

    mp_bearer_token = fields.Char(
        string="Production user token",
        help="Mercado Pago customer production user token: https://www.mercadopago.com.mx/developers/en/reference",
        groups="pos_payment_method.group_payment_method_admin")
    mp_webhook_secret_key = fields.Char(
        string="Production secret key",
        help="Mercado Pago production secret key from integration application: https://www.mercadopago.com.mx/developers/panel/app",
        groups="pos_payment_method.group_payment_method_admin")
    mp_id_point_smart = fields.Char(
        string="Terminal S/N",
        help="Enter your Point Smart terminal serial number written on the back of your terminal (after the S/N:)")
    mp_id_point_smart_complet = fields.Char()
    mp_webhook_endpoint = fields.Char(string="Mercado Pago Webhook Endpoint", compute="_compute_mp_webhook_endpoint", readonly=True)

    def _get_terminal_provider_selection(self):
        return super()._get_terminal_provider_selection() + [("mercado_pago", "Mercado Pago")]

    def _compute_mp_webhook_endpoint(self):
        for record in self:
            web_base_url = record.get_base_url()
            record.mp_webhook_endpoint = f"{web_base_url}/pos_mercado_pago/notification"

    def _mp_find_terminal(self, token, point_smart):
        if point_smart == "SBX0000001":
            # Support the simulated terminal for testing
            return "PAX_A910__SBX0000001"

        mercado_pago = MercadoPagoPosRequest(self.env, token)
        data = mercado_pago.call_mercado_pago("GET", "/terminals/v1/list", {}).get("data", {})
        if "terminals" not in data:
            raise UserError(self.env._("Please verify your production user token as it was rejected"))

        # Search for a terminal id that contains the serial number entered by the user
        found_terminal = next((t for t in data["terminals"] if point_smart in t["id"]), None)
        if not found_terminal:
            raise UserError(self.env._("The terminal serial number is not registered on Mercado Pago"))
        return found_terminal.get("id", "")

    def _start_payment(self, amount: float, currency, extra_args: dict):
        if self.payment_provider != "mercado_pago":
            return super()._start_payment(amount, currency, extra_args)

        mercado_pago = MercadoPagoPosRequest(self.env, self.sudo().mp_bearer_token)
        request = {
            "type": "point",
            "config": {
                "point": {
                    "terminal_id": self.mp_id_point_smart_complet,
                },
            },
            "integration_data": {
                "platform_id": MERCADO_PAGO_PLATFORM_ID,
            },
            "expiration_time": "PT30M",
            "external_reference": f"{self.id}_{uuid4().hex}",
            "transactions": {
                "payments": [{"amount": float_repr(amount, min(currency.decimal_places, 2))}],
            },
        }
        response = mercado_pago.call_mercado_pago("POST", "/v1/orders", request, idempotent=True)
        _logger.debug("mp_order_create(), response from Mercado Pago: %s", response)

        return {"transaction_id": response["id"]}

    def _start_reversal(self, amount: float, currency, original_transaction_id: str, extra_args: dict):
        if self.payment_provider != "mercado_pago":
            return super()._start_reversal(amount, currency, original_transaction_id, extra_args)

        mercado_pago = MercadoPagoPosRequest(self.env, self.sudo().mp_bearer_token)
        order = mercado_pago.call_mercado_pago("GET", f"/v1/orders/{original_transaction_id}", {})
        payments = order.get("transactions", {}).get("payments")
        if not payments:
            return {"error": self.env._("Original Mercado Pago payment not found on order %s", original_transaction_id)}

        payment_amount = payments[0]["amount"]
        refund_amount = float_repr(amount, min(currency.decimal_places, 2))
        if refund_amount == payment_amount:
            body = {}
        else:
            body = {"transactions": [{"id": payments[0]["id"], "amount": refund_amount}]}
        response = mercado_pago.call_mercado_pago("post", f"/v1/orders/{original_transaction_id}/refund", body, idempotent=True)
        _logger.debug("mp_order_refund(), response from Mercado Pago: %s", response)

        return {"transaction_id": response["id"], "status": "paid"}

    def _cancel_transaction(self, transaction_id: str):
        if self.payment_provider != "mercado_pago":
            return super()._cancel_transaction(transaction_id)

        return {"error": self.env._("Mercado Pago payments must be cancelled directly on the terminal.")}

    def _get_transaction_status(self, transaction_id: str):
        if self.payment_provider != "mercado_pago":
            return super()._get_transaction_status(transaction_id)

        mercado_pago = MercadoPagoPosRequest(self.env, self.sudo().mp_bearer_token)
        response = mercado_pago.call_mercado_pago("GET", f"/v1/orders/{transaction_id}", {})
        _logger.debug("mp_order_get(), response from Mercado Pago: %s", response)

        if response["status"] in ["processed", "refunded"]:
            return {"status": "paid"}
        if response["status"] == "canceled":
            return {"status": "failed", "error": self.env._("The payment has been cancelled on the terminal.")}
        if response["status"] == "failed":
            return {"status": "failed", "error": self.env._("The payment has been rejected.")}
        if response["status"] == "expired":
            return {"status": "failed", "error": self.env._("The payment has timed out.")}
        return {"status": "pending", "mercado_pago_status": response["status"]}

    def write(self, vals):
        records = super().write(vals)

        if "mp_id_point_smart" in vals or "mp_bearer_token" in vals:
            self.mp_id_point_smart_complet = self._mp_find_terminal(self.mp_bearer_token, self.mp_id_point_smart)

        return records

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for record in records:
            if record.mp_bearer_token:
                record.mp_id_point_smart_complet = record._mp_find_terminal(record.mp_bearer_token, record.mp_id_point_smart)

        return records
