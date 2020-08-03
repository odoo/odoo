from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal


class Portal(CustomerPortal):
    @http.route(['/my/thing', '/my/thing2'], type='http', auth="user", website=True)
    def thing(self, **_):
        return ""
