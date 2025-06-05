from odoo import models, api
from odoo.osv import expression


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    @api.model
    def _load_pos_self_data_domain(self, data, config_id=None):
        if data['pos.config'][0]['self_ordering_mode'] == 'kiosk':
            domain = super()._load_pos_self_data_domain(data, config_id)
            domain = expression.OR([[('is_online_payment', '=', True)], domain])
            return domain
        else:
            return [('is_online_payment', '=', True)]
