# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, http
from odoo.http import request
from odoo.addons.im_livechat.controllers.main import LivechatController


class WebsiteLivechat(LivechatController):

    def _get_guest_name(self):
        visitor_sudo = request.env["website.visitor"]._get_visitor_from_request()
        return _('Visitor #%d', visitor_sudo.id) if visitor_sudo else super()._get_guest_name()

    @http.route(website=True)
    def assets_embed(self, **kwargs):
        return super().assets_embed(**kwargs)
