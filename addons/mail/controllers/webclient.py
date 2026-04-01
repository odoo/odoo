# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import http
from odoo.http import request
from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.mail.tools.discuss import add_guest_to_context, Store


class WebclientController(ThreadController):
    """Routes for the web client."""

    @http.route("/mail/action", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def mail_action(self, fetch_params, context=None):
        """Execute actions and returns data depending on request parameters.
        This is similar to /mail/data except this method can have side effects.
        """
        return self._process_request(fetch_params, context=context)

    @http.route("/mail/data", methods=["POST"], type="jsonrpc", auth="public", readonly=True)
    @add_guest_to_context
    def mail_data(self, fetch_params, context=None):
        """Returns data depending on request parameters.
        This is similar to /mail/action except this method should be read-only.
        """
        return self._process_request(fetch_params, context=context)

    @classmethod
    def _process_request(self, fetch_params, context):
        store = Store()
        if context:
            request.update_context(**context)
        self._process_request_loop(store, fetch_params)
        return store.get_result()

    @classmethod
    def _process_request_loop(self, store: Store, fetch_params):
        for fetch_param in fetch_params:
            name, params, data_id = (
                (fetch_param, None, None)
                if isinstance(fetch_param, str)
                else (fetch_param + [None, None])[:3]
            )
            store.data_id = data_id
            self._process_request_for_all(store, name, params)
            if not request.env.user._is_public():
                self._process_request_for_logged_in_user(store, name, params)
            if request.env.user._is_internal():
                self._process_request_for_internal_user(store, name, params)
        store.data_id = None

    @classmethod
    def _process_request_for_all(self, store: Store, name, params):
        if name == "init_messaging":
            if not request.env.user._is_public():
                user = request.env.user.sudo(False)
                user._init_messaging(store)
        if name == "mail.thread":
            thread = self._get_thread_with_access(
                params["thread_model"],
                params["thread_id"],
                mode="read",
                **params.get("access_params", {}),
            )
            if not thread:
                store.add(
                    request.env[params["thread_model"]].browse(params["thread_id"]),
                    {"hasReadAccess": False, "hasWriteAccess": False},
                    as_thread=True,
                )
            else:
                store.add(thread, request_list=params["request_list"], as_thread=True)

    @classmethod
    def _process_request_for_logged_in_user(self, store: Store, name, params):
        if name == "failures":
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
            found = defaultdict(list)
            for message in notifications.mail_message_id:
                found[message.model].append(message.res_id)
            existing = {
                model: set(request.env[model].browse(ids).exists().ids)
                for model, ids in found.items()
            }
            valid = notifications.filtered(
                lambda n: n.mail_message_id.res_id in existing[n.mail_message_id.model]
            )
            lost = notifications - valid
            # might break readonly status of mail/data, but in really rare cases
            # and solves it by removing useless notifications
            if lost:
                lost.sudo().unlink()  # no unlink right except admin, ok to remove as lost anyway
            valid.mail_message_id._message_notifications_to_store(store)

    @classmethod
    def _process_request_for_internal_user(self, store: Store, name, params):
        if name == "systray_get_activities":
            # sudo: bus.bus: reading non-sensitive last id
            bus_last_id = request.env["bus.bus"].sudo()._bus_last_id()
            groups = request.env["res.users"]._get_activity_groups()
            store.add_global_values(
                activityCounter=sum(group.get("total_count", 0) for group in groups),
                activity_counter_bus_id=bus_last_id,
                activityGroups=groups,
            )
        if name == "mail.canned.response":
            domain = [
                "|",
                ("create_uid", "=", request.env.user.id),
                ("group_ids", "in", request.env.user.all_group_ids.ids),
            ]
            store.add(request.env["mail.canned.response"].search(domain))
        if name == "avatar_card":
            record_id, model = params.get("id"), params.get("model")
            if not record_id or model not in ("res.users", "res.partner"):
                return
            context = {
                "active_test": False,
                "allowed_company_ids": request.env.user._get_company_ids(),
            }
            record = request.env[model].with_context(**context).search([("id", "=", record_id)])
            store.add(record, record._get_store_avatar_card_fields(store.target))
