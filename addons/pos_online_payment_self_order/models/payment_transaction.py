# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _process_pos_online_payment(self):
        super()._process_pos_online_payment()
        for tx in self:
            if tx and tx.pos_order_id and tx.state in ('authorized', 'done'):
                tx.pos_order_id._send_notification_online_payment_status('success')

    def _process(self, provider_code, payment_data):
        tx = super()._process(provider_code, payment_data)
        if tx._is_self_order_payment_confirmed():
            self.env.ref('payment.cron_post_process_payment_tx')._trigger()
        return tx

    def _is_self_order_payment_confirmed(self):
        self.ensure_one()
        return (
            self.pos_order_id
            and self.state in ('authorized', 'done')
            and self.pos_order_id.source in ('mobile', 'kiosk')
        )
