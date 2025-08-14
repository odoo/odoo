# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _process_pos_online_payment(self):
        super()._process_pos_online_payment()
        for tx in self:
            if tx and tx.pos_order_id and tx.state in ('authorized', 'done'):
                tx.pos_order_id._send_notification_online_payment_status('success')
