# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class WebclientController(http.Controller):
    @http.route("/mail/init_messaging", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def mail_init_messaging(self, context=None):
        if not context:
            context = {}
        if not request.env.user._is_public():
            return request.env.user.sudo(False).with_context(**context)._init_messaging()
        guest = request.env["mail.guest"]._get_guest_from_context()
        if guest:
            return guest.with_context(**context)._init_messaging()
        raise NotFound()

    @http.route("/mail/load_message_failures", methods=["POST"], type="json", auth="user", readonly=True)
    def mail_load_message_failures(self):
        domain = [
            ("author_id", "=", request.env.user.partner_id.id),
            ("notification_status", "in", ("bounce", "exception")),
            ("mail_message_id.message_type", "!=", "user_notification"),
            ("mail_message_id.model", "!=", False),
            ("mail_message_id.res_id", "!=", 0),
        ]
        # sudo as to not check ACL, which is far too costly
        # sudo: mail.notification - return only failures of current user as author
        notifications = self.env["mail.notification"].sudo().search(domain, limit=100)
        return {"Message": notifications.mail_message_id._message_notification_format()}
