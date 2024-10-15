from odoo import models, api
from odoo.osv import expression
from odoo.addons import pos_self_order, pos_online_payment


class PosPaymentMethod(pos_online_payment.PosPaymentMethod, pos_self_order.PosPaymentMethod):

    @api.model
    def _load_pos_self_data_domain(self, data):
        if data['pos.config']['data'][0]['self_ordering_mode'] == 'kiosk':
            domain = super()._load_pos_self_data_domain(data)
            domain = expression.OR([[('is_online_payment', '=', True)], domain])
            return domain
        else:
            return [('is_online_payment', '=', True)]
