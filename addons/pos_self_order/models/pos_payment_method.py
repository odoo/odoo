from odoo import models, api


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    # will be overridden.
    def _payment_request_from_kiosk(self, order):
        pass

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        if config.self_ordering_mode == 'kiosk':
            return [('use_payment_terminal', 'in', config._supported_kiosk_payment_terminal()), ('id', 'in', config.payment_method_ids.ids)]
        else:
            return [('id', '=', False)]
