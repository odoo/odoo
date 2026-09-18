# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http

from odoo.addons.web.controllers.session import Session


class SessionWebsite(Session):

    @http.route('/web/session/logout', website=True, multilang=False, sitemap=False)
    def logout(self, redirect='/odoo'):
        return super().logout(redirect=redirect)
