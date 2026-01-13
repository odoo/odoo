from odoo import models, api
from odoo.fields import Domain


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def _allowed_actions_in_self_order(self):
        return super()._allowed_actions_in_self_order() + ['l10n_id_verify_qris_status', 'get_qr_code_url']

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ['qr_code_method']
        return params

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        # overriden to add the qris payment method to the domain
        super_domain = super()._load_pos_self_data_domain(data, config)

        qris_payment_domain = None
        if config.self_ordering_mode == 'kiosk':
            qris_payment_domain = Domain.AND([
                Domain('qr_code_method', '=', 'id_qr'),
                Domain('id', 'in', config.payment_method_ids.ids)
            ])
        if not qris_payment_domain:
            return super_domain

        return Domain.OR([qris_payment_domain, super_domain])

    def _payment_request_from_kiosk(self, order):
        if self.qr_code_method != 'id_qr':
            return super()._payment_request_from_kiosk(order)

        if order.payment_ids and any(payment.payment_method_id == self for payment in order.payment_ids):
            if not self.l10n_id_verify_qris_status(order.uuid):
                return False
            order.action_pos_order_paid()
            order._send_payment_result("Success")
            return True

        return super()._payment_request_from_kiosk(order)
