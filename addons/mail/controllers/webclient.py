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
        request.update_context(**kwargs.get("context", {}))
        res = {}
        if kwargs.get("init_messaging"):
            if not request.env.user._is_public():
                user = request.env.user.sudo(False)
                self._add_to_res(res, user._init_messaging())
            else:
                guest = request.env["mail.guest"]._get_guest_from_context()
                if guest:
                    self._add_to_res(res, guest._init_messaging())
                else:
                    raise NotFound()
        if not request.env.user._is_public():
            self._add_to_res(res, self._process_request_for_logged_in_user(**kwargs))
        return res

    def _process_request_for_logged_in_user(self, **kwargs):
        res = {}
        if kwargs.get("failures"):
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
        if kwargs.get("systray_get_activities"):
            groups = request.env["res.users"]._get_activity_groups()
            self._add_to_res(
                res,
                {
                    "Store": {
                        "activityCounter": sum(group.get("total_count", 0) for group in groups),
                        "activityGroups": groups,
                    }
                },
            )
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
