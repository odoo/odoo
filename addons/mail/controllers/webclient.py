# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class WebclientController(http.Controller):
    """Routes for the web client."""
    @http.route("/mail/action", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def mail_action(self, **kwargs):
        """Execute actions and returns data depending on request parameters.
        This is similar to /mail/data except this method can have side effects.
        """
        return self._process_request(**kwargs)

    @http.route("/mail/data", methods=["POST"], type="json", auth="public", readonly=True)
    @add_guest_to_context
    def mail_data(self, **kwargs):
        """Returns data depending on request parameters.
        This is similar to /mail/action except this method should be read-only.
        """
        return self._process_request(**kwargs)

    def _process_request(self, **kwargs):
        res = {}
        if kwargs.get("init_messaging"):
            context = kwargs.get("context", {})
            if not request.env.user._is_public():
                user = request.env.user.sudo(False)
                user_with_context = user.with_context(**context)
                self._add_to_res(res, user_with_context._init_messaging())
            else:
                guest = request.env["mail.guest"]._get_guest_from_context()
                if guest:
                    guest_with_context = guest.with_context(**context)
                    self._add_to_res(res, guest_with_context._init_messaging())
                else:
                    raise NotFound()
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
            messages_format = notifications.mail_message_id._message_notification_format()
            self._add_to_res(res, {"Message": messages_format})
        return res

    def _add_to_res(self, res, data):
        for key, val in data.items():
            if val:
                if not key in res:
                    res[key] = val
                else:
                    if isinstance(val, list):
                        res[key].extend(val)
                    elif isinstance(val, dict):
                        res[key].update(val)
                    else:
                        assert False, "unsupported return type"
