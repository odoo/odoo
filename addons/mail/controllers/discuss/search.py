# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.fields import Domain
from odoo.http import request
from odoo.addons.mail.tools.discuss import add_guest_to_context, Store


class SearchController(http.Controller):
    @http.route("/discuss/search", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def search(self, term, category_id=None, limit=10):
        store = Store()
        base_domain = Domain("name", "ilike", term) & Domain("channel_type", "!=", "chat")
        priority_conditions = [
            Domain("is_member", "=", True) & base_domain,
            base_domain,
        ]
        channels = request.env["discuss.channel"]
        for domain in priority_conditions:
            remaining_limit = limit - len(channels)
            if remaining_limit <= 0:
                break
            # We are using _search to avoid the default order that is
            # automatically added by the search method. "Order by" makes the query
            # really slow.
            query = channels._search(Domain('id', 'not in', channels.ids) & domain, limit=remaining_limit)
            channels |= channels.browse(query)
        store.add(channels, "_store_channel_fields")
        request.env["res.partner"]._search_for_channel_invite(store, search_term=term, limit=limit)
        return store.get_result()
