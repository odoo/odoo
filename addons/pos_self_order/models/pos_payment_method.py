from odoo import models, api


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    # can be overridden for other payment methods
    def _payment_request_from_kiosk(self, order):
        if order.payment_ids and self.use_payment_terminal and any(payment.payment_method_id == self for payment in order.payment_ids):
            order.action_pos_order_paid()
            order._send_payment_result("Success")
            return True
        else:
            return False

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        if config.self_ordering_mode == 'kiosk':
            return [('use_payment_terminal', '!=', False), ('id', 'in', config.payment_method_ids.ids)]
        else:
            return [('id', '=', False)]
