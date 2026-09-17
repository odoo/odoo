# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.exceptions import UserError


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def l10n_ph_qrph_verify_payment_status(self, order_uuid, amount):
        """ Tell the cashier whether Maya received the payment of the QRPH code shown for an order.

        The amount is what the cashier is collecting right now, which is not necessarily what the
        codes shown so far were minted for: an order added to after a code was handed out is no
        longer bought by it, and Maya keeps honouring codes it can no longer take back.

        :param str order_uuid: uuid of the <pos.order> being collected
        :param float amount: amount of the payment line being collected
        :return: whether the order can be validated
        :rtype: bool
        """
        self.ensure_one()
        if self.payment_method_type != 'bank_qr_code' or self.qr_code_method != 'ph_qrph':
            return True
        if amount is None:
            # Verifying against nothing would let a code minted for a smaller order through.
            raise UserError(self.env._("The amount being collected is needed to verify a QRPH payment."))

        transactions = self.env['l10n_ph.qrph.transaction'].search([
            ('model', '=', 'pos.order'),
            ('model_id', '=', order_uuid),
        ])
        if not transactions:
            raise UserError(self.env._("No QRPH code was generated for this order."))
        return bool(transactions._get_paid_transaction(amount))
