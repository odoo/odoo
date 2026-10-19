from odoo.addons.pos_online_payment.controllers.payment_status import PosPaymentStatus


class PosPaymentStatusSelfOrder(PosPaymentStatus):

    def _update_payment_status_values(self, values, order_sudo, config_sudo):
        super()._update_payment_status_values(values, order_sudo, config_sudo)
        values.update({
            'pos_primary_color': config_sudo.self_ordering_primary_color,
        })
