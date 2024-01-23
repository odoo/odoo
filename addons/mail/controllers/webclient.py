# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context
from odoo.addons.mail.tools.discuss import StoreData

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
        store = StoreData()
        request.update_context(**kwargs.get("context", {}))
        self._process_request_for_all(store, **kwargs)
        if not request.env.user._is_public():
            self._process_request_for_logged_in_user(store, **kwargs)
        if request.env.user._is_internal():
            self._process_request_for_internal_user(store, **kwargs)
        return store.get_result()

    def _process_request_for_all(self, store, **kwargs):
        if kwargs.get("init_messaging"):
            if not request.env.user._is_public():
                user = request.env.user.sudo(False)
                user._init_messaging(store)
            else:
                guest = request.env["mail.guest"]._get_guest_from_context()
                if guest:
                    guest._init_messaging(store)
                else:
                    raise NotFound()

    def _process_request_for_logged_in_user(self, store, **kwargs):
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
            store.add({"Message": messages_format})

    def _process_request_for_internal_user(self, store, **kwargs):
        if kwargs.get("systray_get_activities"):
            groups = request.env["res.users"]._get_activity_groups()
            store.add({
                "Store": {
                    "activityCounter": sum(group.get("total_count", 0) for group in groups),
                    "activityGroups": groups,
                }
            })
