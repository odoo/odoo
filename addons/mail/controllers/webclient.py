# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context
from odoo.addons.mail.tools.discuss import StoreData
from odoo.osv import expression


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
        if "init_messaging" in kwargs:
            if not request.env.user._is_public():
                user = request.env.user.sudo(False)
                user._init_messaging(store)
            else:
                guest = request.env["mail.guest"]._get_guest_from_context()
                if guest:
                    guest._init_messaging(store)
                else:
                    raise NotFound()
            member_domain = [
                ("is_self", "=", True),
                "|",
                ("fold_state", "in", ("open", "folded")),
                ("rtc_inviting_session_id", "!=", False)
            ]
            channels_domain = [("channel_member_ids", "any", member_domain)]
            channel_types = kwargs["init_messaging"].get("channel_types")
            if channel_types:
                channels_domain = expression.AND(
                    [channels_domain, [("channel_type", "in", channel_types)]]
                )
            store.add({"Thread": request.env["discuss.channel"].search(channels_domain)._channel_info()})

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
            # sudo: bus.bus: reading non-sensitive last id
            bus_last_id = request.env["bus.bus"].sudo()._bus_last_id()
            groups = request.env["res.users"]._get_activity_groups()
            store.add({
                "Store": {
                    "activityCounter": sum(group.get("total_count", 0) for group in groups),
                    "activity_counter_bus_id": bus_last_id,
                    "activityGroups": groups,
                }
            })
        if kwargs.get("canned_responses"):
            field_names = ["source", "substitution"]
            domain = [
                "|",
                ("create_uid", "=", request.env.user.id),
                ("group_ids", "in", request.env.user.groups_id.ids),
            ]
            canned_responses = request.env["mail.canned.response"].search_read(domain, field_names)
            store.add({"CannedResponse": canned_responses})
