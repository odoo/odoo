# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
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
