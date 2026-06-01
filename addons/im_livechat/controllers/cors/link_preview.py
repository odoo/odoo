# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import route

from odoo.addons.mail.controllers.link_preview import LinkPreviewController


class LivechatLinkPreviewController(LinkPreviewController):
    @route(
        "/im_livechat/cors/link_preview",
        methods=["POST"],
        type="jsonrpc",
        auth="force_guest",
        cors="*",
    )
    def livechat_link_preview(self, guest_token, message_id):
        self.mail_link_preview(message_id)

    @route(
        "/im_livechat/cors/link_preview/hide",
        methods=["POST"],
        type="jsonrpc",
        auth="force_guest",
        cors="*",
    )
    def livechat_link_preview_hide(self, guest_token, message_link_preview_ids):
        self.mail_link_preview_hide(message_link_preview_ids)
