
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
        """ Polled by the portal invoice page to know when the QRIS payment is done """
        try:
            invoice_sudo = self._document_check_access('account.move', invoice_id, access_token)
        except (AccessError, MissingError):
            return False
        return invoice_sudo.with_company(invoice_sudo.company_id)._l10n_id_portal_update_qris_status()
