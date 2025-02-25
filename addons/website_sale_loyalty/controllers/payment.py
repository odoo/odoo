# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.website_sale.controllers import payment


class PaymentPortal(payment.PaymentPortal):

    def _validate_transaction_for_order(self, transaction, sale_order):
        """Update programs & rewards before finalizing transaction.

        :param payment.transaction transaction: The payment transaction
        :param int order_id: The id of the sale order to pay
        :raise: ValidationError if the order amount changed after updating rewards
        """
        super()._validate_transaction_for_order(transaction, sale_order)
        if sale_order.exists():
            initial_amount = sale_order.amount_total
            sale_order._update_programs_and_rewards()
            if sale_order.currency_id.compare_amounts(sale_order.amount_total, initial_amount):
                raise ValidationError(
                    _("Cannot process payment: applied reward was changed or has expired.")
                )
