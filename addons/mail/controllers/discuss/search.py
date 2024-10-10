# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context
from odoo.addons.mail.tools.discuss import Store


class SearchController(http.Controller):
    @http.route("/discuss/search", methods=["POST"], type="json", auth="public")
    @add_guest_to_context
    def search(self, term, category_id=None, limit=8):
        return self.get_search_store(term, category_id, limit).get_result()

    def get_search_store(self, term, category_id, limit):
        store = Store()
        if not category_id or category_id == "channels":
            channel_fields = ["name", "channel_type", "avatar_cache_key"]
            channels = request.env["discuss.channel"].search_fetch([
                ("parent_channel_id", "=", None),
                ("channel_type", "=", "channel"),
                ("name", "ilike", term),
            ], channel_fields, limit=limit)
            store.add("discuss.channel", channels.read(channel_fields))
        if not category_id or category_id == "chats":
            users = request.env["res.users"].search([
                ('id', '!=', request.env.user.id),
                ('active', '=', True),
                ('share', '=', False),
                ('name', 'ilike', term),
            ], limit=limit)
            store.add(users.partner_id)
        return store
