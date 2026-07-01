# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_payment.controllers.portal import PortalAccount as AccountPaymentPortal


class PortalAccount(AccountPaymentPortal):

    def _get_common_page_view_values(self, *args, **kwargs):
        """Overwrite of `account_payment` to acknowledge the related document is an invoice."""
        return super()._get_common_page_view_values(*args, is_invoice=True, **kwargs)
