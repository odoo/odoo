# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.osv import expression
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context
from odoo.addons.mail.tools.discuss import Store


class SearchController(http.Controller):
    @http.route("/discuss/search", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def search(self, term, category_id=None, limit=8):
        store = Store()
        self.get_search_store(store, search_term=term, limit=limit)
        return store.get_result()

    def get_search_store(self, store: Store, search_term, limit):
        base_domain = [("name", "ilike", search_term), ("channel_type", "!=", "chat")]
        priority_conditions = [
            [("is_member", "=", True), *base_domain],
            base_domain
        ]
        channels = self.env["discuss.channel"]
        for domain in priority_conditions:
            remaining_limit = limit - len(channels)
            if remaining_limit <= 0:
                break
            # We are using _search to avoid the default order that is
            # automatically added by the search method. "Order by" makes the query
            # really slow.
            query = channels._search(expression.AND([[("id", "not in", channels.ids)], domain]), limit=remaining_limit)
            channels |= channels.browse(query)
        store.add(channels)
        request.env["res.partner"]._search_for_channel_invite(store, search_term=search_term, limit=limit)

    def _load_channels_domain_1(self, channel_type=None, important=False):
        if not channel_type:
            if important:
                return [("channel_type", "in", ("channel", "group")), ("is_member", "=", True), ("message_needaction", "=", True)]
            return [("channel_type", "in", ("channel", "group")), ("is_member", "=", True)]
        if important:
            return [("channel_type", "=", channel_type), ("is_member", "=", True), ("message_needaction", "=", True)]
        return [("channel_type", "=", channel_type), ("is_member", "=", True)]

    def _load_channels_domain_2(self, channel_type=None, important=False):
        if not channel_type:
            if important:
                return [
                    ("channel_type", "not in", ("channel", "group")),
                    ("channel_member_ids", "any", [("is_self", "=", True), ("is_pinned", "=", True), ("message_unread", "=", True)]),
                ]
            return [
                ("channel_type", "not in", ("channel", "group")),
                ("channel_member_ids", "any", [("is_self", "=", True), ("is_pinned", "=", True)]),
            ]
        if important:
            return [
                ("channel_type", "=", channel_type),
                ("channel_member_ids", "any", [("is_self", "=", True), ("is_pinned", "=", True), ("message_unread", "=", True)]),
            ]
        return [
            ("channel_type", "=", channel_type),
            ("channel_member_ids", "any", [("is_self", "=", True), ("is_pinned", "=", True)]),
        ]

    def _load_channels(self, store, channel_types, limit, offset, by_name, important=False):
        if not channel_types:
            domain_1 = self._load_channels_domain_1(important=important)
            domain_2 = self._load_channels_domain_2(important=important)
            domain = expression.OR([domain_1, domain_2])
        elif "channel" in channel_types:
            domain = self._load_channels_domain_1(channel_type="channel", important=important)
        elif "chat" in channel_types and "group" in channel_types:
            domain_1 = self._load_channels_domain_1(channel_type="group", important=important)
            domain_2 = self._load_channels_domain_2(channel_type="chat", important=important)
            domain = expression.OR([domain_1, domain_2])
        else:
            domain = self._load_channels_domain_2(channel_types[0], important=important)
        channels = self.env["discuss.channel"].search(domain, order="name ASC" if by_name else "last_interest_dt DESC", limit=limit, offset=offset)
        store.add(channels)
        new_from_important = important
        new_offset = len(channels) + offset
        return channels, new_from_important, new_offset

    @http.route("/discuss/pinned_channels/load", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def pinned_channels_load(self, offset=0, from_important=True, limit=100, channel_types=None, by_name=False):
        # 2 different queries because the 2 sub-queries together with OR are less efficient
        # member_domain = [("channel_type", "in", ("channel", "group")), ("is_member", "=", True)]
        # pinned_member_domain = [
        #         ("channel_type", "not in", ("channel", "group")),
        #         ("channel_member_ids", "any", [("is_self", "=", True), ("is_pinned", "=", True)]),
        #     ]
        store = Store()
        channels_1 = self.env["discuss.channel"]
        channels_2 = self.env["discuss.channel"]
        if from_important and not by_name:
            channels_1, new_from_important, new_offset = self._load_channels(store=store, channel_types=channel_types, limit=limit, offset=offset, by_name=by_name, important=True)
        if len(channels_1) < limit:
            channels_2, new_from_important, new_offset = self._load_channels(store=store, channel_types=channel_types, limit=limit - len(channels_1), offset=offset, by_name=by_name)
        return {
            "storeData": store.get_result(),
            "offset": new_offset,
            "from_important": new_from_important,
            "all_loaded": len(channels_1) + len(channels_2) < limit
        }
