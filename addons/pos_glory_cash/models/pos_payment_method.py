from odoo import fields, models


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    glory_websocket_address = fields.Char('Cash Machine IP')
    glory_username = fields.Char('Cash Machine Username')
    glory_password = fields.Char('Cash Machine Password')

    def _get_payment_method_type(self):
        return super()._get_payment_method_type() + [('glory_cash', 'Cash Machine (Glory)')]

    def _load_pos_data_fields(self, config_id):
        return super()._load_pos_data_fields(config_id) + ['glory_websocket_address', 'glory_username', 'glory_password']
