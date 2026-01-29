# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.fields import Domain
from odoo.http import request
from odoo.addons.mail.tools.discuss import Store


class MailboxController(http.Controller):
    @http.route("/mail/mailbox/messages", methods=["POST"], type="jsonrpc", auth="user", readonly=True)
    def discuss_mailbox_messages(self, mailbox_id, fetch_params=None):
        """
        :param mailbox_id: 'inbox', 'history', 'starred', 'comments', 'mentioning', 'tracking'
        :param fetch_params: dictionary of parameters for _message_fetch
        """
        domain = self._get_mailbox_domain(mailbox_id)
        res = request.env["mail.message"]._message_fetch(domain, **(fetch_params or {}))
        messages = res.pop("messages")
        store = Store()
        fields_params = {"add_followers": True} if mailbox_id == "inbox" else {}
        store.add(messages, "_store_message_fields", fields_params=fields_params)
        return {**res, "data": store.get_result(), "messages": messages.ids}

    def _get_mailbox_domain(self, mailbox_id):
        """Override to add module-specific mailbox types."""
        partner_id = request.env.user.partner_id.id
        user_notified_domain = Domain("notification_ids", "any", [("res_partner_id", "=", partner_id)])
        if mailbox_id == "inbox":
            return Domain("needaction", "=", True)
        if mailbox_id == "history":
            return Domain("needaction", "=", False)
        if mailbox_id == "starred":
            return Domain("starred_partner_ids", "in", [partner_id])
        if mailbox_id == "comments":
            return Domain.AND([user_notified_domain, Domain("message_type", "=", "comment")])
        if mailbox_id == "mentioning":
            return Domain.AND([
                user_notified_domain,
                Domain("message_type", "=", "comment"),
                Domain("partner_ids", "in", partner_id),
            ])
        if mailbox_id == "tracking":
            return Domain.AND([user_notified_domain, Domain("tracking_value_ids", "!=", False)])

        raise ValueError(request.env._("Unexpected mailbox id %(id)s", id=mailbox_id))
