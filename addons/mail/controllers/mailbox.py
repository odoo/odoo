# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Domain
from odoo.http import request
from odoo.addons.mail.controllers.webclient import WebclientController
from odoo.addons.mail.tools.discuss import Store


class MailboxController(WebclientController):
    @classmethod
    def _process_request_for_logged_in_user(self, store: Store, name, params):
        """Override to mailbox messages."""
        super()._process_request_for_logged_in_user(store, name, params)
        message_fetch_domain = None
        if name == "/mail/inbox/messages":
            message_fetch_domain = Domain("needaction", "=", True)
            request.update_context(add_inbox_fields=True)
        if name == "/mail/history/messages":
            message_fetch_domain = Domain("needaction", "=", False)
        if name == "/mail/starred/messages":
            message_fetch_domain = Domain("starred_partner_ids", "in", [request.env.user.partner_id.id])
        if message_fetch_domain:
            self._resolve_messages(
                store,
                domain=message_fetch_domain,
                fetch_params=params and params.get("fetch_params"),
            )
