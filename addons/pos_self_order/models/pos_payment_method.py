from odoo import models, api


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    # will be overridden.
    def _payment_request_from_kiosk(self, order):
        pass

    # will be overridden.
    @api.model
    def _load_pos_self_data_domain(self, data, config):
        return [('id', '=', False)]
