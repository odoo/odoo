from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.libs.debug_log import DebugLog

from odoo.addons.website_sale.controllers import payment

_debug = DebugLog(__name__)


class PaymentPortal(payment.PaymentPortal):
    def _check_transaction_for_order(self, transaction, sale_order):
        super()._check_transaction_for_order(transaction, sale_order)
        if sale_order.exists():
            initial_amount = sale_order.amount_total
            sale_order._update_programs_and_rewards()
            if sale_order.currency_id.compare_amounts(
                sale_order.amount_total, initial_amount
            ):
                _debug.logic(
                    "payment_amount_changed",
                    order=sale_order.id,
                    initial=initial_amount,
                    current=sale_order.amount_total,
                )
                raise ValidationError(
                    request.env._(
                        "Cannot process payment: applied reward was changed or has expired.\n"
                        "Please refresh the page and try again."
                    )
                )
