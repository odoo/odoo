import logging

from odoo import fields, models, _
from odoo.exceptions import AccessError, UserError

from .mercado_pago_pos_request import MercadoPagoPosRequest

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('mercado_pago', 'Mercado Pago')]

    mp_id_point_smart_complet = fields.Char(copy=False)

    def force_pdv(self):
        """
        Triggered in debug mode when the user wants to force the "PDV" mode.
        It calls the Mercado Pago API to set the terminal mode to "PDV".
        """
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("Do not have access to fetch token from Mercado Pago"))

        mercado_pago = MercadoPagoPosRequest(self.sudo().pos_payment_provider_id.mp_bearer_token)
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
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("Do not have access to fetch token from Mercado Pago"))

        mercado_pago = MercadoPagoPosRequest(self.sudo().pos_payment_provider_id.mp_bearer_token)
        # Call Mercado Pago for payment intend creation
        resp = mercado_pago.call_mercado_pago("post", f"/point/integration-api/devices/{self.mp_id_point_smart_complet}/payment-intents", infos)
        _logger.debug("mp_payment_intent_create(), response from Mercado Pago: %s", resp)
        return resp

    def mp_payment_intent_get(self, payment_intent_id):
        """
        Called from frontend to get the last payment intend from Mercado Pago
        """
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("Do not have access to fetch token from Mercado Pago"))

        mercado_pago = MercadoPagoPosRequest(self.sudo().pos_payment_provider_id.mp_bearer_token)
        # Call Mercado Pago for payment intend status
        resp = mercado_pago.call_mercado_pago("get", f"/point/integration-api/payment-intents/{payment_intent_id}", {})
        _logger.debug("mp_payment_intent_get(), response from Mercado Pago: %s", resp)
        return resp

    def mp_payment_intent_cancel(self, payment_intent_id):
        """
        Called from frontend to cancel a payment intent in Mercado Pago
        """
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("Do not have access to fetch token from Mercado Pago"))

        mercado_pago = MercadoPagoPosRequest(self.sudo().pos_payment_provider_id.mp_bearer_token)
        # Call Mercado Pago for payment intend cancelation
        resp = mercado_pago.call_mercado_pago("delete", f"/point/integration-api/devices/{self.mp_id_point_smart_complet}/payment-intents/{payment_intent_id}", {})
        _logger.debug("mp_payment_intent_cancel(), response from Mercado Pago: %s", resp)
        return resp

    def write(self, vals):
        res = super().write(vals)
        for record in self:
            if 'pos_payment_provider_id' in vals and record.use_payment_terminal == 'mercado_pago':
                record.mp_id_point_smart_complet = record._find_terminal(record.pos_payment_provider_id.mp_bearer_token, record.terminal_identifier)
        return res

    def create(self, vals):
        records = super().create(vals)
        for record in records:
            if 'pos_payment_provider_id' in vals and record.use_payment_terminal == 'mercado_pago':
                record.mp_id_point_smart_complet = record._find_terminal(record.pos_payment_provider_id.mp_bearer_token, record.terminal_identifier)
        return records

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
