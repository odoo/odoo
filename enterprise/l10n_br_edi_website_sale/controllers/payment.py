# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.website_sale.controllers import payment


class PaymentPortal(payment.PaymentPortal):
    def _validate_transaction_for_order(self, transaction, sale_order):
        """Override. Copy over the default EDI payment method from the payment method to the SO."""
        sale_order.l10n_br_edi_payment_method = transaction.payment_method_id.l10n_br_edi_payment_method
        return super()._validate_transaction_for_order(transaction, sale_order)
