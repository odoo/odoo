from odoo import models, api
from odoo.osv import expression


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    @api.model
    def _load_pos_self_data_domain(self, data):
        if data['pos.config']['data'][0]['self_ordering_mode'] == 'kiosk':
            domain = super()._load_pos_self_data_domain(data)
            domain = expression.OR([[('payment_method_type', '=', 'online')], domain])
            return domain
        else:
            return [('payment_method_type', '=', 'online')]
