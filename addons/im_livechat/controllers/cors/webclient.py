# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route
from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.im_livechat.tools.misc import force_guest_env


class WebClient(WebclientController):
    """Override to add CORS support."""

    @route("/im_livechat/cors/store", methods=["POST"], type="jsonrpc", auth="public", cors="*", readonly=lambda self, *_: self._is_mail_fetch_readonly())
    def livechat_store(self, guest_token="", **kwargs):
        force_guest_env(guest_token, raise_if_not_found=False)
        return self.mail_store(**kwargs)
