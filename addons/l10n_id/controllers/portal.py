
from odoo.addons.account.controllers.portal import PortalAccount
from odoo import http
from odoo.http import request


class Portal(PortalAccount):
    @http.route()
    def portal_my_invoice_detail(self, *args, **kw):
        """ Override
        force QR code generation from QRIS to come only from portal"""
        request.update_context(is_online_qr=True)
        return super().portal_my_invoice_detail(*args, **kw)
