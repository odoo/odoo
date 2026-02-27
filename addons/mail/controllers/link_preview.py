# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.mail.tools.discuss import add_guest_to_context


class LinkPreviewController(ThreadController):
    @http.route("/mail/link_preview", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def mail_link_preview(self, message_id, **kwargs):
        if not request.env["mail.link.preview"]._is_link_preview_enabled():
            return
        message = self._get_message_with_access(int(message_id), "create", **kwargs)
        if not message:
            return
        # sudo: mail.message - access mail.link.preview through an accessible message is allowed
        message.env["mail.link.preview"].sudo()._create_from_message_and_notify(
            message, request_url=request.httprequest.url_root
        )

    @http.route("/mail/link_preview/hide", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def mail_link_preview_hide(self, message_link_preview_ids, **kwargs):
        # sudo: access check is done below using message_id
        link_preview_sudo = (
            request.env["mail.message.link.preview"]
            .sudo()
            .search([("id", "in", message_link_preview_ids)])
        )
        if any(
            not self._get_message_with_access(link_preview.message_id.id, "create", **kwargs)
            for link_preview in link_preview_sudo
        ):
            return
        link_preview_sudo._hide_and_notify()
