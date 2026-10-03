# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _l10n_ph_qrph_settle_kiosk_payment(self, transaction):
        """ Register the QRPH payment of this kiosk order and send its customer to the receipt.

        The payment is recorded by the server that had Maya confirm it, never on the kiosk's say-so:
        the kiosk only ever displays a code. A kiosk that crashes or loses the network right after
        the customer paid therefore no longer leaves them with an order nobody paid for.

        Doing this twice amounts to doing it once, as Maya repeats a notification it was given no
        answer to and the customer may ask about their payment in the meantime. The result is sent
        again either way, so a kiosk that missed the message is not left waiting on a paid order.

        :param transaction: the paid <l10n_ph.qrph.transaction> being settled
        """
        self.ensure_one()
        payment_method = self.config_id.payment_method_ids.filtered(
            lambda method: method._l10n_ph_is_kiosk_qrph()
        )[:1]
        if not payment_method:
            return

        if self.state == 'draft':
            if transaction.currency_id.compare_amounts(transaction.amount, self.amount_total) < 0:
                # The customer went back to their order and added to it after this code was handed
                # out. Maya still honours the code, so it is payable, but it no longer buys the
                # order it was minted against: settling on it would hand over the difference.
                return
            self.add_payment({
                'amount': self.amount_total,
                'payment_date': fields.Datetime.now(),
                'payment_method_id': payment_method.id,
                'pos_order_id': self.id,
            })
            self.action_pos_order_paid()
            transaction.settled_date = fields.Datetime.now()
        self._send_payment_result('Success')
