from odoo import api, models
from odoo.osv import expression


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def _payment_request_from_kiosk(self, order):
        if self.use_payment_terminal != 'stripe':
            return super()._payment_request_from_kiosk(order)
        else:
            return self.stripe_payment_intent(order.amount_total)

    @api.model
    def _load_pos_self_data_domain(self, data):
        domain = super()._load_pos_self_data_domain(data)
        if data['pos.config'][0]['self_ordering_mode'] == 'kiosk':
            domain = expression.OR([
                [('use_payment_terminal', '=', 'stripe'), ('id', 'in', data['pos.config'][0]['payment_method_ids'])],
                domain
            ])
        return domain
