# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.tools import float_round

from odoo.addons.payment_razorpay import const


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    def _razorpay_get_limit_exceed_warning(self, amount, currency_id):
        """ Return a warning message when the maximum payment amount is exceeded.

        :param float amount: The amount to be paid.
        :param currency_id: The currency of the amount.
        :return: A warning message when the maximum payment amount is exceeded.
        :rtype: str
        """
        self.ensure_one()

        if not amount or self.provider_code != 'razorpay':
            return ""

        # Try to get the maximum amount based on the transaction from which this token was created.
        Transaction = self.env['payment.transaction']
        primary_tx = Transaction.search(
            [('token_id', '=', self.id), ('operation', 'not in', ['offline', 'online_token'])],
            limit=1,
        )
        if primary_tx:
            mandate_max_amount = primary_tx._razorpay_get_mandate_max_amount()
        else:  # Get the maximum amount based on the token's payment method code.
            pm = self.payment_method_id.primary_payment_method_id or self.payment_method_id
            mandate_max_amount_INR = const.MANDATE_MAX_AMOUNT.get(
                pm.code, const.MANDATE_MAX_AMOUNT['card']
            )
            mandate_max_amount = Transaction._razorpay_convert_inr_to_currency(
                mandate_max_amount_INR, currency_id
            )

        # Return the warning message if the amount exceeds the maximum amount; else an empty string.
        if amount > mandate_max_amount:
            return _(
                "You can not pay amounts greater than %(currency_symbol)s %(max_amount)s with this"
                " payment method",
                currency_symbol=currency_id.symbol,
                max_amount=float_round(mandate_max_amount, precision_digits=0),
            )
        return ""
