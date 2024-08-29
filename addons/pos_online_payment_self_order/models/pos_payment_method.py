from odoo import models, api
from odoo.addons import point_of_sale
from odoo.osv import expression


class PosPaymentMethod(models.Model, point_of_sale.PosPaymentMethod):

    @api.model
    def _load_pos_self_data_domain(self, data):
        if data['pos.config']['data'][0]['self_ordering_mode'] == 'kiosk':
            domain = super()._load_pos_self_data_domain(data)
            domain = expression.OR([[('is_online_payment', '=', True)], domain])
            return domain
        else:
            return [('is_online_payment', '=', True)]
