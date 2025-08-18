from odoo import models, api
from odoo.fields import Domain


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        if config.self_ordering_mode == 'kiosk':
            domain = super()._load_pos_self_data_domain(data, config)
            domain = Domain.OR([[('is_online_payment', '=', True), ('id', 'in', config.payment_method_ids.ids)], domain])
            return domain
        else:
            return [('is_online_payment', '=', True)]
