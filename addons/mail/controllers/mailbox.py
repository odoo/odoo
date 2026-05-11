# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command, Domain
from odoo.http import request

from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.mail.tools.store_handler import store_handler


class MailboxController(WebclientController):
    @classmethod
    def _update_bookmark(cls, store, message_id, bookmarked):
        bookmark_messages = request.env["mail.message"]
        if message := cls._get_message_with_access(message_id, mode="read"):
            command = Command.link if bookmarked else Command.unlink
            # sudo: mail.message - users can bookmark messages they can read
            message.sudo().bookmarked_partner_ids = [command(request.env.user.partner_id.id)]
            bookmark_messages |= message
        cls._send_bookmark_update(store, bookmark_messages)

    @classmethod
    def _send_bookmark_update(cls, store, messages):
        if not messages:
            return
        bus_store = Store(bus_channel=request.env.user)
        for cur_store in [store, bus_store]:
            cur_store.add(messages, ["is_bookmarked"])
            cur_store.add_global_values(request.env.user._store_bookmark_box_global_fields)

    @store_handler("add_bookmark", readonly=False)
    def store_add_bookmark(self, store: Store, message_id):
        self._update_bookmark(store, message_id, bookmarked=True)

    @store_handler("remove_bookmark", readonly=False)
    def store_remove_bookmark(self, store: Store, message_id):
        self._update_bookmark(store, message_id, bookmarked=False)

    @store_handler("remove_all_bookmarks", readonly=False)
    def store_remove_all_bookmarks(self, store: Store):
        # sudo: mail.message - users can remove their bookmarks
        messages_su = (
            request.env["mail.message"].sudo().search_fetch([("is_bookmarked", "=", True)])
        )
        messages_su.bookmarked_partner_ids = [Command.unlink(request.env.user.partner_id.id)]
        self._send_bookmark_update(store, messages_su)

    @store_handler("/mail/inbox/messages")
    def store_mailbox_messages(self, store: Store, fetch_params=None):
        request.update_context(add_inbox_fields=True)
        self._resolve_messages(
            store,
            domain=Domain("needaction", "=", True),
            fetch_params=fetch_params,
        )

    @store_handler("/mail/history/messages")
    def store_history_messages(self, store: Store, fetch_params=None):
        self._resolve_messages(
            store,
            domain=Domain("needaction", "=", False),
            fetch_params=fetch_params,
        )

    @store_handler("/mail/bookmark/messages")
    def store_bookmark_messages(self, store: Store, fetch_params=None):
        self._resolve_messages(
            store,
            domain=Domain("bookmarked_partner_ids", "in", [request.env.user.partner_id.id]),
            fetch_params=fetch_params,
        )
