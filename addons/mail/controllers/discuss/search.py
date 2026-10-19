# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.fields import Domain
from odoo.http import request

from odoo.addons.mail.tools.discuss import Store, mail_route


class SearchController(http.Controller):
    @mail_route("/discuss/search", methods=["POST"], type="jsonrpc", auth="public")
    def search(self, term, limit=10):
        name_ilike_domain = Domain("name", "ilike", term)
        name_ilike_domain_for_members = name_ilike_domain
        member_based_name_types = request.env["discuss.channel"]._member_based_naming_channel_types()
        if term and member_based_name_types:
            member_name_domain = Domain("partner_id.name", "ilike", term) | Domain(
                "guest_id.name",
                "ilike",
                term,
            )
            # Only for member scoped conditions: without membership filtering, scanning
            # every channel's members is very slow (and useless since groups are not
            # accessible for non-members).
            name_ilike_domain_for_members |= Domain(
                [
                    ("channel_member_ids", "any", member_name_domain),
                    ("channel_type", "in", member_based_name_types),
                    ("name", "=", False),
                ],
            )
        channel_type_domain = Domain("channel_type", "!=", "chat")
        base_domain = name_ilike_domain & channel_type_domain
        base_domain_for_members = name_ilike_domain_for_members & channel_type_domain
        priority_conditions = [
            base_domain_for_members & Domain("self_member_id.is_favorite", "=", True),
            base_domain_for_members & Domain("is_member", "=", True),
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
            query = channels._search(
                Domain("id", "not in", channels.ids) & domain,
                limit=remaining_limit,
            )
            channels |= channels.browse(query)
        store = Store()
        store.add(channels, "_store_channel_fields").add(channels.self_member_id, ["is_favorite"])
        request.env["res.partner"]._search_for_channel_invite(store, search_term=term, limit=limit)
        return store
