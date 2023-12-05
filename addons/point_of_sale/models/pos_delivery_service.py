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
    access_token_expiration_timestamp = fields.Float()
    journal_id = fields.Many2one('account.journal',
        string='Journal',
        domain=['|', '&', ('type', '=', 'cash'), ('pos_payment_method_ids', '=', False), ('type', '=', 'bank')],
        ondelete='restrict')
    active = fields.Boolean("Active", default=True)
    is_test = fields.Boolean("Test Mode", help='Run transactions in the test environment.')
    config_id = fields.Many2one('pos.config', string='Point of Sale')

    def _new_order(self, order_id):
        # notify the pos sessions / preparation screens
        pass

    @api.model
    def _get_access_token(self) -> str:
        self.ensure_one()
        return (self.access_token_expiration_timestamp or 0) > time.time() \
            and self.access_token or self._refresh_access_token()

    @api.model
    def _refresh_access_token(self) -> str:
        pass

    @api.model
    def _upload_menu(self):
        pass
