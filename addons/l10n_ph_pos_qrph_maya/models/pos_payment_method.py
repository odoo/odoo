# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.exceptions import UserError

from odoo.addons.l10n_ph_qrph_maya import const


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def l10n_ph_qrph_verify_payment_status(self, order_uuid, company_id, amount):
        """ Tell the cashier whether Maya received the payment of the QRPH code shown for an order.

        Only the latest code of the order is looked at: it is the one on the cashier's screen, minted
        for the payment line being collected. The earlier ones belong to the payment lines collected
        before, which are not stored until the order is paid: a code paid for 70 must not vouch for
        the 30 that follow it.

        The amount is what the cashier is collecting right now, which is not necessarily what that
        code was minted for: an order added to after a code was handed out is no longer bought by
        it, and Maya keeps honouring codes it can no longer take back.

        :param str order_uuid: uuid of the <pos.order> being collected
        :param int company_id: id of the <res.company> the order is collected for, so that the
            transactions are not looked up by uuid alone
        :param float amount: amount of the payment line being collected
        :return: whether the order can be validated
        :rtype: bool
        """
        self.ensure_one()
        if self.payment_method_type != 'bank_qr_code' or self.qr_code_method != const.QR_METHOD:
            return True
        if amount is None:
            # Verifying against nothing would let a code minted for a smaller order through.
            raise UserError(self.env._("The amount being collected is needed to verify a QRPH payment."))

        transactions = self.env['l10n_ph.qrph.transaction'].search([
            ('pos_order_uuid', '=', order_uuid),
            ('company_id', '=', company_id),
        ])
        if not transactions:
            raise UserError(self.env._("No QRPH transaction was generated for this order."))
        # The transactions are ordered most recent first.
        return bool(transactions[:1]._get_paid_transaction(amount))
