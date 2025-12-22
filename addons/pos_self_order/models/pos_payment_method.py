from odoo import models, api


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    # will be overridden.
    def _payment_request_from_kiosk(self, order):
        pass

    @api.model
    def _load_pos_self_data_domain(self, data):
        if data['pos.config']['data'][0]['self_ordering_mode'] == 'kiosk':
            return [('use_payment_terminal', 'in', ['adyen', 'stripe']), ('id', 'in', data['pos.config']['data'][0]['payment_method_ids'])]
        else:
            [('id', '=', False)]
