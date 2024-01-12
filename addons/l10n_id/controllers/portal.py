
from odoo.addons.account.controllers.portal import PortalAccount
from odoo import http
from odoo.http import request

class Portal(PortalAccount):
    @http.route()
    def portal_my_invoice_detail(self, **kw):
        """ Override
        force QR code generation from QRIS to come only from portal"""
        request.env.context = {**request.env.context, "from_portal": True}
        return super().portal_my_invoice_detail(**kw)
