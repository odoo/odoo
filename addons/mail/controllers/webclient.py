# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo.fields import Domain
from odoo.http import request

from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.mail.models.mail_message import SHARE_DOMAIN
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.mail.tools.store_handler import store_handler


class WebclientController(ThreadController):
    """Generic store handlers for the web client."""

    def _process_request_loop(self, store: Store, fetch_params):
        # aggregate of messages to return, to batch them in a single query when all the fetch
        # params have been processed
        request.update_context(messages=request.env["mail.message"], add_inbox_fields=False, add_chatter_fields=False)
        super()._process_request_loop(store, fetch_params)
        if messages := request.env.context["messages"]:
            fields_params = {
                **({"inbox_fields": True} if request.env.context["add_inbox_fields"] else {}),
                **({"chatter_fields": True} if request.env.context["add_chatter_fields"] else {}),
            }
            if request.env.context["add_inbox_fields"]:
                # sudo: bus.bus: reading non-sensitive last id
                bus_last_id = request.env["bus.bus"].sudo()._bus_last_id()
                store.add(messages, "_store_message_fields", fields_params=fields_params)
                for records in messages._records_by_model_name().values():
                    if not isinstance(records, request.env.registry["mail.thread"]):
                        continue
                    store.add(
                        records,
                        lambda res: (
                            # sudo: mail.thread: users can read their own message_needaction_counter on the thread
                            res.attr("message_needaction_counter", sudo=True),
                            res.attr("message_needaction_counter_bus_id", bus_last_id),
                        ),
                        as_thread=True,
                    )
            else:
                store.add(messages, "_store_message_fields", fields_params=fields_params)

    @store_handler("mail.thread", audience="everyone")
    def store_mail_thread(
        self, store, thread_model, thread_id, request_list, access_params=None, **kwargs
    ):
        thread = self._get_thread_with_access(
            thread_model, thread_id, mode="read", **(access_params or {})
        )
        if not thread:
            thread = request.env[thread_model].browse(thread_id)
            store.add(thread, {"hasReadAccess": False, "hasWriteAccess": False}, as_thread=True)
        else:
            store.add(
                thread,
                "_store_thread_fields",
                fields_params={"request_list": request_list, "chatter_fields": True},
                as_thread=True,
            )

    @store_handler("init_messaging", audience="everyone")
    def store_init_messaging(self, store: Store):
        if request.env.user._is_internal():
            # sudo: bus.bus: reading non-sensitive last id
            bus_last_id = request.env["bus.bus"].sudo()._bus_last_id()
            store.add_global_values(
                lambda res: self._store_init_messaging_global_fields(res, bus_last_id),
            )

    @store_handler("res.partner", audience="everyone")
    def store_get_res_partner(self, store: Store, id):
        partner = request.env["res.partner"].search_fetch([("id", "=", id)])
        store.add(partner, "_store_partner_fields")

    @store_handler("res.users", audience="everyone")
    def store_get_res_users(self, store: Store, id):
        user = request.env["res.users"].search_fetch([("id", "=", id)])
        store.add(user, "_store_user_fields")

    @store_handler("mail.activity")
    def store_get_mail_activity(self, store: Store, ids):
        activities = request.env["mail.activity"].with_context(active_test=False).search_fetch(
            [("id", "in", ids)]
        )
        store.add(activities, "_store_activity_fields")

    @store_handler("/mail/poll_option/votes", audience="everyone")
    def store_poll_option_votes(self, store: Store, poll_option_id):
        # sudo - mail.poll.option: validated by "_get_thread_with_access" afterwards.
        if opt_sudo := request.env["mail.poll.option"].sudo().search([("id", "=", poll_option_id)]):
            message = opt_sudo.poll_id.start_message_id
            if self._get_thread_with_access(message.model, message.res_id, mode="read"):
                store.add(opt_sudo.vote_ids, "_store_vote_fields")

    @store_handler("failures", audience="logged_in")
    def store_get_failures(self, store: Store):
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
        # might break readonly status of mail/store, but in really rare cases
        # and solves it by removing useless notifications
        if lost:
            lost.sudo().unlink()  # no unlink right except admin, ok to remove as lost anyway
        store.add(valid.mail_message_id, "_store_notification_fields")

    @store_handler("/mail/thread/messages", audience="everyone", readonly=False)
    def store_get_thread_messages(
        self,
        store: Store,
        thread_model,
        thread_id,
        fetch_params=None,
        access_params=None,
        share_only=False,
        **params,
    ):
        request.update_context(add_chatter_fields=True)
        if thread := self._get_thread_with_access(
            thread_model,
            thread_id,
            mode="read",
            **(access_params or {}),
        ):
            self._prepare_fetch_context(thread, access_params)
            domain = Domain.TRUE
            if (
                share_only
                or not request.env.user._is_internal()
                or not thread.sudo(False).has_access("read")
            ):
                domain = self._get_fetch_share_domain(thread, **params)
            messages = self._resolve_messages(
                store,
                domain=domain,
                thread=thread,
                fetch_params=fetch_params,
                sudo=thread.env.su,
            )
            if not request.env.user._is_public():
                messages.set_message_done()

    @store_handler("systray_get_activities", audience="logged_in")
    def store_systray_get_activities(self, store: Store):
        if not self.env.user._is_internal():
            return
        # sudo: bus.bus: reading non-sensitive last id
        bus_last_id = request.env["bus.bus"].sudo()._bus_last_id()
        groups = request.env["res.users"]._get_activity_groups()
        store.add_global_values(
            activities_to_assign_count=request.env["res.users"]._get_activities_to_assign_count(),
            activityCounter=sum(group.get("total_count", 0) for group in groups),
            activity_counter_bus_id=bus_last_id,
            activityGroups=groups,
        )

    @store_handler("mail.canned.response")
    def store_mail_canned_response(self, store: Store):
        domain = [
            "|",
            ("create_uid", "=", request.env.user.id),
            ("group_ids", "in", request.env.user.all_group_ids.ids),
        ]
        store.add(
            request.env["mail.canned.response"].search_fetch(domain),
            "_store_canned_response_fields",
        )

    @store_handler("avatar_card")
    def store_avatar_card(self, store: Store, id=None, model=None):
        if not id or model not in self._get_supported_avatar_card_models():
            return
        context = {
            "active_test": False,
            "allowed_company_ids": request.env.user._get_company_ids(),
        }
        record = request.env[model].with_context(**context).search([("id", "=", id)])
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
        user._store_bookmark_box_global_fields(res, bus_last_id)

    @classmethod
    def _get_supported_avatar_card_models(self):
        return ["res.users", "res.partner"]

    @classmethod
    def _resolve_messages(
        self,
        store: Store,
        /,
        *,
        domain=None,
        thread=None,
        fetch_params=None,
        add_to_store=True,
        sudo=False,
    ):
        fetch_res = (
            request.env["mail.message"]
            .sudo(sudo)
            ._message_fetch(domain, thread=thread, **(fetch_params or {}))
        )
        messages = fetch_res.pop("messages")
        if add_to_store:
            request.update_context(messages=messages | request.env.context["messages"])
        store.resolve_data_request(
            lambda res: (
                [res.attr(k, v) for k, v in fetch_res.items()],
                res.many("messages", [], value=messages),
            ),
        )
        return messages

    @classmethod
    def _prepare_fetch_context(cls, thread, access_params=None):
        """To override to update the context before fetching thread messages if needed."""
        return

    @classmethod
    def _get_fetch_share_domain(cls, records, **params):
        """Return the domain to fetch messages in a shared context like portal.
        In this context, internal users have the same visibility as non-internal users.
        Message types are further filtered per model via `_get_customer_portal_message_types`."""
        return (
            Domain([("model", "=", records._name), ("res_id", "in", records.ids)])
            & SHARE_DOMAIN
            & Domain("message_type", "in", records._get_customer_portal_message_types())
            & ~records.env["mail.message"]._get_empty_domain()
        )
