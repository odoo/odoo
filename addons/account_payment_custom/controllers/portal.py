# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_payment.controllers.portal import PortalAccount as AccountPaymentPortal


class Portal(AccountPaymentPortal):

    def _get_common_page_view_values(self, *args, **kwargs):
        """Override of `account_payment` to inject is_invoice=True in the kwargs."""
        return super()._get_common_page_view_values(*args, is_invoice=True, **kwargs)
