from odoo import api, fields, models, _
import time

class PosDeliveryService(models.Model):
    _name = 'pos.delivery.service'
    _description = "Point of Sale Delivery Methods"

    def _get_available_services(self):
        return []

    name = fields.Char(required=True)
    service = fields.Selection(string="Delivery Service", selection=lambda self: self._get_available_services(), required=True)
    image_128 = fields.Image("Delivery Service Logo", max_width=128, max_height=128)
    client_id = fields.Char("Client ID", help='', copy=False, required=True)
    client_secret = fields.Char("Client Secret", copy=False, required=True)
    access_token = fields.Char(copy=False)
    access_token_expiration_timestamp = fields.Float(copy=False)
    payment_method_id = fields.Many2one('pos.payment.method', string='Payment Method', required=True, copy=False, help="The payment method and its journal should be created especially for this delivery service.")
    active = fields.Boolean("Active", default=True)
    is_test = fields.Boolean("Test Mode", help='Run transactions in the test environment.')
    config_ids = fields.Many2many('pos.config', 'pos_config_delivery_service_rel', 'delivery_service_id', 'config_id', string='Point of Sale')

    def _new_order(self, order_id):
        # notify the pos sessions / preparation screens
        pass

    def _get_access_token(self) -> str:
        self.ensure_one()
        return (self.access_token_expiration_timestamp or 0) > time.time() \
            and self.access_token or self._refresh_access_token()

    def _refresh_access_token(self) -> str:
        pass

    def _upload_menu(self):
        pass

    def _accept_order(self, id: int, status: str = ""):
        pass

    def _reject_order(self, id: int, rejected_reason: str = "busy"):
        pass

    def _get_delivery_acceptation_time(self):
        pass
