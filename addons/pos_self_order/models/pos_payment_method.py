from odoo import models, api
from odoo.addons import point_of_sale


class PosPaymentMethod(point_of_sale.PosPaymentMethod):

    # will be overridden.
    def _payment_request_from_kiosk(self, order):
        pass

    @api.model
    def _load_pos_self_data_domain(self, data):
        if data['pos.config']['data'][0]['self_ordering_mode'] == 'kiosk':
            return [('use_payment_terminal', 'in', ['adyen', 'stripe'])]
        else:
            [('id', '=', False)]
