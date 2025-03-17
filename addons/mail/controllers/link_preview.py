# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.mail.tools.discuss import add_guest_to_context


class LinkPreviewController(http.Controller):
    @http.route("/mail/link_preview", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def mail_link_preview(self, message_id):
        if not request.env["mail.link.preview"]._is_link_preview_enabled():
            return
        guest = request.env["mail.guest"]._get_guest_from_context()
        message = guest.env["mail.message"].search([("id", "=", int(message_id))])
        if not message:
            return
        if not message.is_current_user_or_guest_author and not guest.env.user._is_admin():
            return
        guest.env["mail.link.preview"].sudo()._create_from_message_and_notify(
            message, request_url=request.httprequest.url_root
        )

    @http.route("/mail/link_preview/hide", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def mail_link_preview_hide(self, message_link_preview_ids):
        guest = request.env["mail.guest"]._get_guest_from_context()
        # sudo: access check is done below using message_id
        link_preview_sudo = guest.env["mail.message.link.preview"].sudo().search([("id", "in", message_link_preview_ids)])
        if not guest.env.user._is_admin() and any(
            not link_preview.message_id.is_current_user_or_guest_author
            for link_preview in link_preview_sudo
        ):
            return
        link_preview_sudo._hide_and_notify()
