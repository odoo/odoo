# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class MailboxController(http.Controller):
    @http.route("/mail/inbox/messages", methods=["POST"], type="json", auth="user")
    def discuss_inbox_messages(self, before=None, after=None, limit=30, around=None):
        partner_id = request.env.user.partner_id.id
        domain = [("needaction", "=", True)]
        return (request.env["mail.message"]
                ._message_fetch(domain, before, after, around, limit)
                ._message_format_personalize(partner_id))

    @http.route("/mail/history/messages", methods=["POST"], type="json", auth="user")
    def discuss_history_messages(self, before=None, after=None, limit=30):
        domain = [("needaction", "=", False)]
        return request.env["mail.message"]._message_fetch(domain, before, after, limit=limit).message_format()

    @http.route("/mail/starred/messages", methods=["POST"], type="json", auth="user")
    def discuss_starred_messages(self, before=None, after=None, limit=30):
        domain = [("starred_partner_ids", "in", [request.env.user.partner_id.id])]
        return request.env["mail.message"]._message_fetch(domain, before, after, limit=limit).message_format()
