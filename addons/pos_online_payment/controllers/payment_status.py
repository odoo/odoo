from odoo.tools.image import image_data_uri

from odoo.addons.payment.controllers.payment_status import PaymentStatus


class PosPaymentStatus(PaymentStatus):

    def get_payment_status_template_xmlid(self, tx):
        if tx and tx.pos_order_id:
            return 'pos_online_payment.pos_payment_status'
        return super().get_payment_status_template_xmlid(tx)

    def _get_payment_status_values(self, tx):
        values = super()._get_payment_status_values(tx)
        if tx and tx.pos_order_id:
            order_sudo = tx.pos_order_id  # `tx` is already sudoed by the controller.
            config_sudo = order_sudo.config_id

            self._update_payment_status_values(values, order_sudo, config_sudo)
        return values

    def _update_payment_status_values(self, values, order_sudo, config_sudo):
        values.update({
            'pos_tracking_number': order_sudo.tracking_number,
            'pos_is_restaurant': config_sudo.module_pos_restaurant,
            'pos_logo': config_sudo.logo and image_data_uri(config_sudo.logo),
            'pos_company_name': config_sudo.company_id.name,
        })
