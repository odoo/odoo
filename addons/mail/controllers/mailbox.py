# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command, Domain
from odoo.http import request
from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.mail.tools.discuss import Store


class MailboxController(WebclientController):
    @classmethod
    def _process_request_for_logged_in_user(self, store: Store, name, params):
        """Override to mailbox messages."""
        super()._process_request_for_logged_in_user(store, name, params)
        bookmark_messages = request.env["mail.message"]
        if name in ["add_bookmark", "remove_bookmark"]:
            if message := self._get_message_with_access(params["message_id"], mode="read"):
                command = Command.link if name == "add_bookmark" else Command.unlink
                # sudo: mail.message - users can bookmark messages they can read
                message.sudo().bookmarked_partner_ids = [command(request.env.user.partner_id.id)]
                bookmark_messages |= message
        if name == "remove_all_bookmarks":
            # sudo: mail.message - users can remove their bookmarks
            messages_su = request.env["mail.message"].sudo().search_fetch([("is_bookmarked", "=", True)])
            messages_su.bookmarked_partner_ids = [Command.unlink(request.env.user.partner_id.id)]
            bookmark_messages |= messages_su
        if bookmark_messages:
            bus_store = Store(bus_channel=request.env.user)
            for cur_store in [store, bus_store]:
                cur_store.add(bookmark_messages, ["is_bookmarked"])
                cur_store.add_global_values(request.env.user._store_bookmark_box_global_fields)
            bus_store.bus_send()
        message_fetch_domain = None
        if name == "/mail/inbox/messages":
            message_fetch_domain = Domain("needaction", "=", True)
            request.update_context(add_inbox_fields=True)
        if name == "/mail/history/messages":
            message_fetch_domain = Domain("needaction", "=", False)
        if name == "/mail/bookmark/messages":
            message_fetch_domain = Domain("bookmarked_partner_ids", "in", [request.env.user.partner_id.id])
        if message_fetch_domain:
            self._resolve_messages(
                store,
                domain=message_fetch_domain,
                fetch_params=params and params.get("fetch_params"),
            )
