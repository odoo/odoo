# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.website_sale.controllers import payment


class PaymentPortal(payment.PaymentPortal):

    def _create_transaction(self, *args, **kwargs):
        tx = super()._create_transaction(*args, **kwargs)
        for order in tx.sale_order_ids:
            if (
                tx.provider_id.code == 'custom' and tx.provider_id.custom_mode == 'on_site' and
                order.coupon_point_ids.filtered(lambda pe: pe.coupon_id.program_id.program_type in ['gift_card', 'ewallet']).coupon_id
            ):
                raise ValidationError(
                    _("Cannot process payment: Gift cards and eWallets are not compatible with on site payment")
                )
        return tx

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
                    _(
                        "Cannot process payment: applied reward was changed or has expired.\n"
                        "Please refresh the page and try again."
                    )
                )
