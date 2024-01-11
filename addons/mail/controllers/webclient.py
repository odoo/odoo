# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class WebclientController(http.Controller):
    """Routes for the web client."""
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

    @http.route("/mail/data", methods=["POST"], type="json", auth="public", readonly=True)
    def mail_data(self, **kwargs):
        """Returns data depending on request parameters."""
        res = defaultdict(list)
        if kwargs.get("failures") and not request.env.user._is_public():
            domain = [
                ("author_id", "=", request.env.user.partner_id.id),
                ("notification_status", "in", ("bounce", "exception")),
                ("mail_message_id.message_type", "!=", "user_notification"),
                ("mail_message_id.model", "!=", False),
                ("mail_message_id.res_id", "!=", 0),
            ]
            # sudo as to not check ACL, which is far too costly
            # sudo: mail.notification - return only failures of current user as author
            notifications = request.env["mail.notification"].sudo().search(domain, limit=100)
            res["Message"].append(notifications.mail_message_id._message_notification_format())
        return res
