from odoo import models, api


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    # can be overridden for other payment methods
    def _payment_request_from_kiosk(self, order):
        pass

    @api.model
    def _load_pos_self_data_domain(self, data):
        config = data['pos.config']
        if config.self_ordering_mode == 'kiosk':
            return [('id', 'in', config.payment_method_ids.ids), '|', ('type', '=', 'cash'), ('payment_provider', '!=', False)]
        return [('id', '=', False)]
