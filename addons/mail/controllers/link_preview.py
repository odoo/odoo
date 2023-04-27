# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class LinkPreviewController(http.Controller):
    @http.route("/mail/link_preview", methods=["POST"], type="json", auth="public")
    def mail_link_preview(self, message_id, clear=None):
        if not request.env["mail.link.preview"].sudo()._is_link_preview_enabled():
            return
        guest = request.env["mail.guest"]._get_guest_from_request(request)
        message = guest.env["mail.message"].search([("id", "=", int(message_id))])
        if not message:
            return
        if not message.is_current_user_or_guest_author and not guest.env.user._is_admin():
            return
        if clear:
            guest.env["mail.link.preview"].sudo()._clear_link_previews(message)
        guest.env["mail.link.preview"].sudo()._create_link_previews(message)

    @http.route("/mail/link_preview/delete", methods=["POST"], type="json", auth="public")
    def mail_link_preview_delete(self, link_preview_id):
        guest = request.env["mail.guest"]._get_guest_from_request(request)
        link_preview_sudo = guest.env["mail.link.preview"].sudo().search([("id", "=", int(link_preview_id))])
        if not link_preview_sudo:
            return
        if not link_preview_sudo.message_id.is_current_user_or_guest_author and not guest.env.user._is_admin():
            return
        link_preview_sudo._delete_and_notify()
