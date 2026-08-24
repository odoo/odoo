# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.web.controllers.home import Home as WebHome
from odoo.addons.mail.tools.discuss import add_guest_to_context


class Home(WebHome):

    @http.route()
    @add_guest_to_context
    def web_client(self, s_action=None, **kw):
        return super().web_client(s_action, **kw)
