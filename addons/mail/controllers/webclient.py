# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
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
            notifications.mail_message_id._message_notifications_to_store(store)
        elif name == "load_messaging_menu_data":
            self._load_messaging_menu_data(store, params)

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

    @classmethod
    def _load_messaging_menu_data(self, store: Store, params: dict):
        """Load messaging menu data for diffrent tabs."""
        tab = params.get("tab", "main")
        load_limit = int(params.get("limit", 30))
        offset = int(params.get("offset", 0))
        tab_loaders = {
            "inbox": self._load_inbox_data,
            "channel": self._load_channel_data,
            "chat": self._load_chat_data,
            "main": self._load_main_data,
        }
        loader = tab_loaders.get(tab)
        if loader:
            loader(store, offset, load_limit)

    def _get_messages(offset: int, limit: int | None, needaction: bool = True):
        """Fetch messages"""
        domain = [("needaction", "=", needaction)]
        return request.env["mail.message"].search(domain, limit=limit, offset=offset, order="id DESC")

    def _get_channels(domain: list = [], offset: int = 0, limit: int | None = None, seprate_by_needaction: bool = False):
        """Fetch channels based on the provided domain, limit, and channel types."""
        channels = request.env["discuss.channel"].search(domain, order="last_interest_dt DESC")
        needaction_channels = channels.filtered(lambda c: c.message_needaction)
        history_channels = channels.filtered(lambda c: not c.message_needaction)
        if seprate_by_needaction:
            return {
                "needaction": needaction_channels,
                "history": history_channels,
            }
        channels = (needaction_channels + history_channels)
        if limit:
            channels = channels[offset:offset + limit]
        return channels

    @classmethod
    def _load_inbox_data(self, store: Store, offset: int, limit: int):
        """Load data for the inbox tab."""
        inbox_msgs = self._get_messages(offset, limit, True)
        inbox_msgs_count = request.env["mail.message"].search_count([("needaction", "=", True)])
        remaining_limit = limit - len(inbox_msgs)
        history_msgs = request.env["mail.message"].browse()
        if remaining_limit > 0:
            history_msgs = self._get_messages(max(0, offset - inbox_msgs_count), remaining_limit, False)
        all_msgs = inbox_msgs + history_msgs
        store.add(all_msgs, add_followers=True).resolve_data_request(
            count=len(all_msgs),
        )

    @classmethod
    def _load_channel_data(self, store: Store, offset: int, limit: int):
        """Load data for channels tab."""
        domain = [("channel_type", "=", "channel")]
        channels = self._get_channels(domain, offset, limit, False)
        store.add(channels).resolve_data_request(count=len(channels))

    @classmethod
    def _load_chat_data(self, store: Store, offset: int, limit: int):
        """Load data for chat tab."""
        domain = [("channel_type", "in", ["chat", "group"])]
        channels = self._get_channels(domain, offset, limit, False)
        store.add(channels).resolve_data_request(count=len(channels))

    @classmethod
    def _load_main_data(self, store: Store, offset: int, limit: int):
        """Load data for main tab with comprehensive thread and message fetching."""
        inbox_msgs = self._get_messages(0, None, True)
        domain = [("channel_type", "in", ["chat", "group", "channel"])]
        all_channels = self._get_channels(domain, 0, None, True)
        needaction_channels = all_channels.get("needaction", request.env["discuss.channel"])
        history_channels = all_channels.get("history", request.env["discuss.channel"])

        def get_sort_key(record):
            date_val = None
            if record._name == "discuss.channel":
                date_val = record.last_interest_dt
            elif record._name == "mail.message":
                date_val = record.write_date
            return date_val or datetime.datetime.min
        combined_all_unread = [*inbox_msgs, *needaction_channels]
        sorted_all_unread = sorted(
            combined_all_unread,
            key=get_sort_key,
            reverse=True,
        )
        limited_threads_list = [*sorted_all_unread, *history_channels][offset:offset + limit]
        final_messages = request.env["mail.message"]
        final_channels = request.env["discuss.channel"]
        for record in limited_threads_list:
            if record._name == "mail.message":
                final_messages |= record
            elif record._name == "discuss.channel":
                final_channels |= record
        store.add(final_channels)
        store.add(final_messages, add_followers=True)
        store.resolve_data_request(
            count=len(limited_threads_list),
        )
