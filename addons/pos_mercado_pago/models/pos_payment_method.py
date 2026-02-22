import logging
import hashlib

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

from .mercado_pago_pos_request import MercadoPagoPosRequest

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    mp_bearer_token = fields.Char(
        string="Production user token",
        help='Mercado Pago customer production user token: https://www.mercadopago.com.mx/developers/en/reference',
        groups="point_of_sale.group_pos_manager")
    mp_webhook_secret_key = fields.Char(
        string="Production secret key",
        help='Mercado Pago production secret key from integration application: https://www.mercadopago.com.mx/developers/panel/app',
        groups="point_of_sale.group_pos_manager")
    mp_id_point_smart = fields.Char(
        string="Terminal S/N",
        help="Enter your Point Smart terminal serial number written on the back of your terminal (after the S/N:)")
    mp_id_point_smart_complet = fields.Char()

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('mercado_pago', 'Mercado Pago')]

    def _check_special_access(self):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("Do not have access to fetch token from Mercado Pago"))

    def force_pdv(self):
        """
        Triggered in debug mode when the user wants to force the "PDV" mode.
        It calls the Mercado Pago API to set the terminal mode to "PDV".
        Uses the terminals API: PATCH /terminals/v1/setup
        Reference: https://www.mercadopago.com.ar/developers/es/reference/in-person-payments/point/terminals/update-operation-mode/patch
        """
        self._check_special_access()

        mercado_pago = MercadoPagoPosRequest(self.sudo().mp_bearer_token)
        _logger.info('Calling Mercado Pago to force the terminal mode to "PDV"')

        payload = {
            "terminals": [
                {
                    "id": self.mp_id_point_smart_complet,
                    "operating_mode": "PDV"
                }
            ]
        }
        
        # Use the terminals API endpoint
        resp = mercado_pago.call_mercado_pago("patch", "/terminals/v1/setup", payload)
        
        # Check if the response contains the updated terminals
        if 'terminals' in resp and len(resp['terminals']) > 0:
            if resp['terminals'][0].get("operating_mode") != "PDV":
                raise UserError(_("Unexpected Mercado Pago response: %s", resp))
            _logger.debug("Successfully set the terminal mode to 'PDV'.")
        else:
            raise UserError(_("Unexpected Mercado Pago response: %s", resp))
        
        return None

    def _prepare_mp_order_payload(self, infos):
        """
        Prepare the order payload for Mercado Pago Point API.
        This method can be inherited to customize the payload structure.
        
        :param infos: Dictionary containing order information from frontend
        :return: Dictionary with the order payload
        """
        return {
            "type": "point",
            "external_reference": infos.get("external_reference"),
            "expiration_time": "PT16M", 
            "transactions": {
                "payments": [
                    {
                        "amount": f"{infos.get('amount', 0) / 100.0:.2f}"
                    }
                ]
            },
            "config": {
                "point": {
                    "terminal_id": self.mp_id_point_smart_complet,
                    "print_on_terminal": "seller_ticket",
                    "ticket_number": infos.get("ticket_number")
                },
                "payment_method": {
                    "default_type": infos.get("card_type")
                }
            },
            "description": f"Point of Sale payment - {infos.get('external_reference')}",
        }

    def mp_order_create(self, infos):
        """
        Called from frontend for creating an order in Mercado Pago Point
        """
        self._check_special_access()

        mercado_pago = MercadoPagoPosRequest(self.sudo().mp_bearer_token)
        
        order_payload = self._prepare_mp_order_payload(infos)        
        idempotency_key = hashlib.sha256(str(order_payload).encode()).hexdigest()
        resp = mercado_pago.call_mercado_pago("post", "/v1/orders", order_payload, idempotency_key=idempotency_key)
        _logger.debug("mp_order_create(), response from Mercado Pago: %s", resp)
        return resp

    def mp_order_get(self, order_id):
        """
        Called from frontend to get the order status from Mercado Pago Point
        Uses the Orders API: GET /v1/orders/{id}
        Reference: https://www.mercadopago.com.ar/developers/es/reference/in-person-payments/point/orders/get-order/get
        """
        self._check_special_access()

        mercado_pago = MercadoPagoPosRequest(self.sudo().mp_bearer_token)
        # Call Mercado Pago for order status using Orders API
        resp = mercado_pago.call_mercado_pago("get", f"/v1/orders/{order_id}", {})
        _logger.debug("mp_order_get(), response from Mercado Pago: %s", resp)
        return resp

    def mp_get_payment_status(self, payment_id):
        """
        Called from frontend to get the payment status from Mercado Pago
        """
        self._check_special_access()

        mercado_pago = MercadoPagoPosRequest(self.sudo().mp_bearer_token)

        resp = mercado_pago.call_mercado_pago("get", f"/v1/payments/{payment_id}", {})
        _logger.debug("mp_get_payment_status(), response from Mercado Pago: %s", resp)
        return resp

    def mp_order_cancel(self, order_id):
        """
        Called from frontend to cancel an order in Mercado Pago Point
        Uses the Orders API: /v1/orders/{order_id}/cancel
        """
        self._check_special_access()

        mercado_pago = MercadoPagoPosRequest(self.sudo().mp_bearer_token)
        
        idempotency_key = hashlib.sha256(str(order_id).encode()).hexdigest()        
        resp = mercado_pago.call_mercado_pago("post", f"/v1/orders/{order_id}/cancel", {}, idempotency_key=idempotency_key)
        _logger.debug("mp_order_cancel(), response from Mercado Pago: %s", resp)
        return resp

    def _find_terminal(self, token, point_smart):
        mercado_pago = MercadoPagoPosRequest(token)
        data = mercado_pago.call_mercado_pago("get", "/terminals/v1/list", {})
        if 'data' in data and 'terminals' in data['data']:
            # Search for a terminal id that contains the serial number entered by the user
            found_terminal = next((terminal for terminal in data['data']['terminals'] if point_smart in terminal['id']), None)

            if not found_terminal:
                raise UserError(_("The terminal serial number is not registered on Mercado Pago"))

            return found_terminal.get('id', '')
        else:
            raise UserError(_("Please verify your production user token as it was rejected"))

    def write(self, vals):
        records = super().write(vals)

        if 'mp_id_point_smart' in vals or 'mp_bearer_token' in vals:
            self.mp_id_point_smart_complet = self._find_terminal(self.mp_bearer_token, self.mp_id_point_smart)

        return records

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for record in records:
            if record.mp_bearer_token:
                record.mp_id_point_smart_complet = record._find_terminal(record.mp_bearer_token, record.mp_id_point_smart)

        return records
