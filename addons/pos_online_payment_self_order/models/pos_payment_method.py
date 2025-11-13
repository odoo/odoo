from odoo import models, api
from odoo.fields import Domain


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        super_domain = super()._load_pos_self_data_domain(data, config)

        online_payment_domain = None
        if config.self_ordering_mode == 'kiosk':
            online_payment_domain = Domain.AND([
                Domain('is_online_payment', '=', True),
                Domain('id', 'in', config.payment_method_ids.ids)
            ])
        elif config.self_order_online_payment_method_id:
            online_payment_domain = Domain('id', '=', config.self_order_online_payment_method_id.id)

        if not online_payment_domain:
            return super_domain

        return Domain.OR([online_payment_domain, super_domain])
