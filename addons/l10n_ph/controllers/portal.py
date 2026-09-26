# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request

from odoo.addons.account.controllers.portal import PortalAccount


class L10nPhPortalAccount(PortalAccount):

    @http.route()
    def portal_my_invoice_detail(self, *args, report_type=None, **kw):
        # EXTENDS account
        # Minting a QRPH code opens a payment on Maya, so only do it when the customer is looking at
        # the invoice: a code printed in a downloaded PDF would be stale by the time it is scanned.
        if report_type in (None, 'html'):
            request.update_context(is_online_qr=True)
        return super().portal_my_invoice_detail(*args, report_type=report_type, **kw)
