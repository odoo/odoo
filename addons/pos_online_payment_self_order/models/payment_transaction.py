# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _process_pos_online_payment(self):
        previous_states = {
            tx.id: tx.pos_order_id.state if tx.pos_order_id else False
            for tx in self
        }
        super()._process_pos_online_payment()
        for tx in self:
            if tx and tx.pos_order_id and tx.state in ('authorized', 'done'):
                pos_order = tx.pos_order_id
                # No cashier validates a self-order, it is finalized once paid
                if pos_order.source in ('kiosk', 'mobile') and pos_order.state == 'draft' and pos_order._is_pos_order_paid():
                    pos_order._process_saved_order(False)
                if previous_states.get(tx.id) == 'draft':
                    tx.pos_order_id._send_self_order_receipt()
                tx.pos_order_id._send_notification_online_payment_status('success')
