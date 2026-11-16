# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_payment.controllers.portal import PortalAccount as AccountPaymentPortal


class Portal(AccountPaymentPortal):

    def _get_invoice_payment_options_context(self, *args, **kwargs):
        """Override of `account_payment` to exclude pay_on_invoice providers for invoices."""
        return {**super()._get_invoice_payment_options_context(*args, **kwargs), 'is_invoice': True}
