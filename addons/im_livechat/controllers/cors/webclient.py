# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route

from odoo.addons.mail.controllers.webclient import WebclientController


class WebClient(WebclientController):
    """Override to add CORS support."""

    @route(
        "/im_livechat/cors/store",
        methods=["POST"],
        type="jsonrpc",
        auth="force_guest",
        cors="*",
        readonly=lambda self, *_: self._is_mail_fetch_readonly(),
    )
    def livechat_store(self, guest_token="", **kwargs):
        return self.mail_store(**kwargs)
