# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _l10n_ph_qrph_settle_kiosk_payment(self, payment_method, transaction):
        """ Register the payment of this kiosk order with a paid QRPH transaction.

        Only a draft order is paid, so this can be called again for an order that is already paid.

        :param payment_method: the <pos.payment.method> the kiosk customer is paying with
        :param transaction: the paid <l10n_ph.qrph.transaction> being settled
        :return: whether the order is paid, which it is not if the transaction no longer buys it
        :rtype: bool
        """
        self.ensure_one()
        if self.state == 'draft':
            if transaction.currency_id.compare_amounts(transaction.amount, self.amount_total) < 0:
                # The customer went back to their order and added to it after this code was handed
                # out. Maya still honours the code, so it is payable, but it no longer buys the
                # order it was minted against: settling on it would hand over the difference.
                return False
            self.add_payment({
                'amount': self.amount_total,
                'payment_date': fields.Datetime.now(),
                'payment_method_id': payment_method.id,
                'pos_order_id': self.id,
            })
            self.action_pos_order_paid()
            # sudo: the kiosk may read the transactions of its orders, not write them.
            transaction.sudo().settled_date = fields.Datetime.now()
        return True
