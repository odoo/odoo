# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
                # sudo: bus.bus: reading non-sensitive last id
                bus_last_id = request.env["bus.bus"].sudo()._bus_last_id()
                store.add_global_values(
                    lambda res: self._store_init_messaging_global_fields(res, bus_last_id),
                )
        if name == "mail.thread":
            thread = self._get_thread_with_access(
                params["thread_model"],
                params["thread_id"],
                mode="read",
                **params.get("access_params", {}),
            )
            if not thread:
                thread = request.env[params["thread_model"]].browse(params["thread_id"])
                store.add(thread, {"hasReadAccess": False, "hasWriteAccess": False}, as_thread=True)
            else:
                store.add(
                    thread,
                    "_store_thread_fields",
                    fields_params={"request_list": params["request_list"]},
                    as_thread=True,
                )

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
            store.add(notifications.mail_message_id, "_store_notification_fields")

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
            store.add(
                request.env["mail.canned.response"].search_fetch(domain),
                "_store_canned_response_fields",
            )
        if name == "avatar_card":
            record_id, model = params.get("id"), params.get("model")
            if not record_id or model not in self._get_supported_avatar_card_models():
                return
            context = {
                "active_test": False,
                "allowed_company_ids": request.env.user._get_company_ids(),
            }
            record = request.env[model].with_context(**context).search([("id", "=", record_id)])
            store.add(record, "_store_avatar_card_fields")

    @classmethod
    def _store_init_messaging_global_fields(cls, res: Store.FieldList, bus_last_id):
        user = request.env.user.sudo(False)
        res.attr(
            "inbox",
            {
                "counter": user.partner_id._get_needaction_count(),
                "counter_bus_id": bus_last_id,
                "id": "inbox",
                "model": "mail.box",
            },
        )
        res.attr(
            "starred",
            {
                "counter": user.env["mail.message"].search_count(
                    [("starred_partner_ids", "in", user.partner_id.ids)],
                ),
                "counter_bus_id": bus_last_id,
                "id": "starred",
                "model": "mail.box",
            },
        )

    @classmethod
    def _get_supported_avatar_card_models(self):
        return ["res.users", "res.partner"]
