# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.mail.tools.discuss import Store


class MailboxController(http.Controller):
    @http.route("/mail/inbox/messages", methods=["POST"], type="jsonrpc", auth="user", readonly=True)
    def discuss_inbox_messages(self, fetch_params=None):
        domain = [("needaction", "=", True)]
        res = request.env["mail.message"]._message_fetch(domain, **(fetch_params or {}))
        messages = res.pop("messages")
        # sudo: bus.bus: reading non-sensitive last id
        bus_last_id = request.env["bus.bus"].sudo()._bus_last_id()
        store = Store().add(
            messages,
            extra_fields=[
                Store.One("thread", [
                    Store.Attr("message_needaction_counter"),
                    Store.Attr("message_needaction_counter_bus_id", bus_last_id)
                ], as_thread=True)
            ],
            add_followers=True
        )
        return {
            **res,
            "data": store.get_result(),
            "messages": messages.ids,
        }

    @http.route("/mail/history/messages", methods=["POST"], type="jsonrpc", auth="user", readonly=True)
    def discuss_history_messages(self, fetch_params=None):
        domain = [("needaction", "=", False)]
        res = request.env["mail.message"]._message_fetch(domain, **(fetch_params or {}))
        messages = res.pop("messages")
        return {
            **res,
            "data": Store().add(messages).get_result(),
            "messages": messages.ids,
        }

    @http.route("/mail/starred/messages", methods=["POST"], type="jsonrpc", auth="user", readonly=True)
    def discuss_starred_messages(self, fetch_params=None):
        domain = [("starred_partner_ids", "in", [request.env.user.partner_id.id])]
        res = request.env["mail.message"]._message_fetch(domain, **(fetch_params or {}))
        messages = res.pop("messages")
        return {
            **res,
            "data": Store().add(messages).get_result(),
            "messages": messages.ids,
        }
