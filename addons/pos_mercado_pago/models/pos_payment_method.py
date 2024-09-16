import logging

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

    @api.onchange('use_payment_terminal')
    def _onchange_use_payment_terminal(self):
        super()._onchange_use_payment_terminal()
        if self.use_payment_terminal == 'mercado_pago' and not self.mp_webhook_secret_key:
            existing_payment_method = self.search([('use_payment_terminal', '=', 'mercado_pago'), ('mp_webhook_secret_key', '!=', False)], limit=1)
            if existing_payment_method:
                self.update({
                    'mp_webhook_secret_key': existing_payment_method.mp_webhook_secret_key,
                    'mp_bearer_token': existing_payment_method.mp_bearer_token
                })

    def _check_special_access(self):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("Do not have access to fetch token from Mercado Pago"))

    def force_pdv(self):
        """
        Triggered in debug mode when the user wants to force the "PDV" mode.
        It calls the Mercado Pago API to set the terminal mode to "PDV".
        """
        self._check_special_access()

        mercado_pago = MercadoPagoPosRequest(self.sudo().mp_bearer_token)
        _logger.info('Calling Mercado Pago to force the terminal mode to "PDV"')

        mode = {"operating_mode": "PDV"}
        resp = mercado_pago.call_mercado_pago("patch", f"/point/integration-api/devices/{self.mp_id_point_smart_complet}", mode)
        if resp.get("operating_mode") != "PDV":
            raise UserError(_("Unexpected Mercado Pago response: %s", resp))
        _logger.debug("Successfully set the terminal mode to 'PDV'.")
        return None

    def mp_payment_intent_create(self, infos):
        """
        Called from frontend for creating a payment intent in Mercado Pago
        """
        self._check_special_access()

        mercado_pago = MercadoPagoPosRequest(self.sudo().mp_bearer_token)
        # Call Mercado Pago for payment intend creation
        resp = mercado_pago.call_mercado_pago("post", f"/point/integration-api/devices/{self.mp_id_point_smart_complet}/payment-intents", infos)
        _logger.debug("mp_payment_intent_create(), response from Mercado Pago: %s", resp)
        return resp

    def mp_payment_intent_get(self, payment_intent_id):
        """
        Called from frontend to get the last payment intend from Mercado Pago
        """
        self._check_special_access()

        mercado_pago = MercadoPagoPosRequest(self.sudo().mp_bearer_token)
        # Call Mercado Pago for payment intend status
        resp = mercado_pago.call_mercado_pago("get", f"/point/integration-api/payment-intents/{payment_intent_id}", {})
        _logger.debug("mp_payment_intent_get(), response from Mercado Pago: %s", resp)
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

    def mp_payment_intent_cancel(self, payment_intent_id):
        """
        Called from frontend to cancel a payment intent in Mercado Pago
        """
        self._check_special_access()

        mercado_pago = MercadoPagoPosRequest(self.sudo().mp_bearer_token)
        # Call Mercado Pago for payment intend cancelation
        resp = mercado_pago.call_mercado_pago("delete", f"/point/integration-api/devices/{self.mp_id_point_smart_complet}/payment-intents/{payment_intent_id}", {})
        _logger.debug("mp_payment_intent_cancel(), response from Mercado Pago: %s", resp)
        return resp

    def _find_terminal(self, token, point_smart):
        mercado_pago = MercadoPagoPosRequest(token)
        data = mercado_pago.call_mercado_pago("get", "/point/integration-api/devices", {})
        if 'devices' in data:
            # Search for a device id that contains the serial number entered by the user
            found_device = next((device for device in data['devices'] if point_smart in device['id']), None)

            if not found_device:
                raise UserError(_("The terminal serial number is not registered on Mercado Pago"))

            return found_device.get('id', '')
        else:
            raise UserError(_("Please verify your production user token as it was rejected"))

    def write(self, vals):
        res = super().write(vals)
        for record in self:
            if record.use_payment_terminal == 'mercado_pago' and 'mp_id_point_smart' in vals or 'mp_bearer_token' in vals:
                record.mp_id_point_smart_complet = record._find_terminal(record.mp_bearer_token, record.mp_id_point_smart)
        return res

    def create(self, vals):
        records = super().create(vals)
        for record in records:
            if record.use_payment_terminal == 'mercado_pago' and record.mp_bearer_token:
                record.mp_id_point_smart_complet = record._find_terminal(record.mp_bearer_token, record.mp_id_point_smart)
        return records
