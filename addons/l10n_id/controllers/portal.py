
from odoo.addons.account.controllers.portal import PortalAccount
from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request


class Portal(PortalAccount):
    @http.route()
    def portal_my_invoice_detail(self, *args, **kw):
        """ Override
        force QR code generation from QRIS to come only from portal"""
        request.update_context(is_online_qr=True)
        return super().portal_my_invoice_detail(*args, **kw)

    @http.route('/l10n_id/qris/status/<int:invoice_id>', type='jsonrpc', auth='public')
    def l10n_id_qris_payment_status(self, invoice_id, access_token=None):
        """
        Tell whether the invoice is paid or in payment.
        To be polled when we want to automatically update the invoice page when its status changes; for example when a QR payment is made.
        Polled by the portal invoice page to know when the QRIS payment has been registered by the webhook
        :returns True if the invoice payment status is 'paid' or 'in_payment'
        """
        try:
            invoice_sudo = self._document_check_access('account.move', invoice_id, access_token)
        except (AccessError, MissingError):
            return False
        return invoice_sudo.payment_state in ('in_payment', 'paid')
