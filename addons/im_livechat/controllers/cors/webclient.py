# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route
from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.im_livechat.tools.misc import force_guest_env


class WebClient(WebclientController):
    """Override to add CORS support."""

    @route("/im_livechat/cors/action", methods=["POST"], type="json", auth="public", cors="*")
    def livechat_action(self, guest_token, **kwargs):
        force_guest_env(guest_token)
        return self.mail_action(**kwargs)

    @route("/im_livechat/cors/data", methods=["POST"], type="json", auth="public", cors="*", readonly=True)
    def livechat_data(self, guest_token, **kwargs):
        force_guest_env(guest_token)
        return self.mail_data(**kwargs)
