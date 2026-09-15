from odoo import models, api
from odoo.osv import expression


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _payment_request_from_kiosk(self, order):
        if self.use_payment_terminal != 'razorpay':
            return super()._payment_request_from_kiosk(order)
        data = {
            'amount': order.amount_total,
            'referenceId': f'{order.config_id.id}/{order.uuid}/{self.id}/{order.currency_id.name}/{order.amount_total}',
        }
        return self.razorpay_make_payment_request(data)

    @api.model
    def _load_pos_self_data_domain(self, data):
        domain = super()._load_pos_self_data_domain(data)
        if data['pos.config']['data'][0]['self_ordering_mode'] == 'kiosk':
            domain = expression.OR([[('use_payment_terminal', '=', 'razorpay')], domain])
        return domain
