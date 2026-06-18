import logging

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

from .mercado_pago_pos_request import MERCADO_PAGO_PLATFORM_ID, MercadoPagoPosRequest

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
    mp_is_test_mode = fields.Boolean(string="Mercado Pago Test Mode", default=False, help="Simulates POS Terminal workflow without the card being present.")
    mp_webhook_endpoint = fields.Char(string="Mercado Pago Webhook Endpoint", compute='_compute_mp_webhook_endpoint', readonly=True)

    @api.model
    def _load_pos_data_fields(self, config):
        return super()._load_pos_data_fields(config) + ['mp_is_test_mode']

    def _get_terminal_provider_selection(self):
        return super()._get_terminal_provider_selection() + [('mercado_pago', 'Mercado Pago')]

    def _allowed_actions_in_self_order(self):
        return super()._allowed_actions_in_self_order() + ['mp_order_create', 'mp_order_get', 'mp_order_simulate']

    def _check_special_access(self):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("Do not have access to fetch token from Mercado Pago"))

    def _compute_mp_webhook_endpoint(self):
        for record in self:
            web_base_url = record.get_base_url()
            record.mp_webhook_endpoint = f"{web_base_url}/pos_mercado_pago/notification"

    def force_pdv(self):
        """
        Triggered in debug mode when the user wants to force the "PDV" mode.
        It calls the Mercado Pago API to set the terminal mode to "PDV".
        """
        self._check_special_access()

        mercado_pago = MercadoPagoPosRequest(self.sudo().mp_bearer_token)
        _logger.info('Calling Mercado Pago to force the terminal mode to "PDV"')

        payload = {"terminals": [{"id": self.mp_id_point_smart_complet, "operating_mode": "PDV"}]}
        resp = mercado_pago.call_mercado_pago("patch", "/terminals/v1/setup", payload)
        terminals = resp.get("terminals")
        if not terminals or terminals[0].get("operating_mode") != "PDV":
            raise UserError(_("Unexpected Mercado Pago response: %s", resp))
        _logger.debug("Successfully set the terminal mode to 'PDV'.")

    def mp_order_create(self, infos):
        """
        Called from frontend to create an order in Mercado Pago
        """
        self._check_special_access()

        mercado_pago = MercadoPagoPosRequest(self.sudo().mp_bearer_token)
        # Identify Odoo as the integrator
        infos['config'] = {
            'point': {
                'terminal_id': self.mp_id_point_smart_complet,
            },
        }
        infos['integration_data'] = {
            'platform_id': MERCADO_PAGO_PLATFORM_ID,
        }
        infos['expiration_time'] = 'PT30M'

        resp = mercado_pago.call_mercado_pago("post", "/v1/orders", infos, idempotent=True)
        _logger.debug("mp_order_create(), response from Mercado Pago: %s", resp)
        return resp

    def mp_order_get(self, order_id):
        """
        Called from frontend to get the order status from Mercado Pago
        """
        self._check_special_access()

        mercado_pago = MercadoPagoPosRequest(self.sudo().mp_bearer_token)
        # Call Mercado Pago for the order status
        resp = mercado_pago.call_mercado_pago("get", f"/v1/orders/{order_id}", {})
        _logger.debug("mp_order_get(), response from Mercado Pago: %s", resp)
        return resp

    def mp_order_refund(self, order_id, amount=None):
        """
        Called from frontend to refund a Mercado Pago order.
        """
        self._check_special_access()

        mercado_pago = MercadoPagoPosRequest(self.sudo().mp_bearer_token)
        if amount is None:
            body = {}
        else:
            order = self.mp_order_get(order_id)
            payments = order.get("transactions", {}).get("payments")
            if not payments:
                return {"errorMessage": _("Original Mercado Pago payment not found on order %s", order_id)}
            body = {"transactions": [{"id": payments[0]["id"], "amount": amount}]}
        resp = mercado_pago.call_mercado_pago("post", f"/v1/orders/{order_id}/refund", body, idempotent=True)
        _logger.debug("mp_order_refund(), response from Mercado Pago: %s", resp)
        return resp

    def mp_order_simulate(self, order_id):
        """ Drive a Mercado Pago order through a simulated terminal status.

        Hits POST /v1/orders/{order_id}/events, which only works on a test
        account (Mercado Pago test accounts still use production-style
        APP_USR- keys). Used to auto-approve test orders end-to-end so the
        cashier can drive the full POS flow without a physical terminal. """
        self._check_special_access()

        mercado_pago = MercadoPagoPosRequest(self.sudo().mp_bearer_token)
        body = {
            'status': 'processed',
            'payment_method_type': 'credit_card',
            'installments': 1,
            'payment_method_id': 'visa',
            'status_detail': 'accredited',
        }
        resp = mercado_pago.call_mercado_pago('post', f"/v1/orders/{order_id}/events", body)
        _logger.debug("mp_order_simulate(), response from Mercado Pago: %s", resp)
        return resp

    def _find_terminal(self, token, point_smart):
        mercado_pago = MercadoPagoPosRequest(token)
        data = mercado_pago.call_mercado_pago("get", "/terminals/v1/list", {}).get('data', {})
        if 'terminals' not in data:
            raise UserError(_("Please verify your production user token as it was rejected"))

        # Search for a terminal id that contains the serial number entered by the user
        found_terminal = next((t for t in data['terminals'] if point_smart in t['id']), None)
        if not found_terminal:
            raise UserError(_("The terminal serial number is not registered on Mercado Pago"))
        return found_terminal.get('id', '')

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
