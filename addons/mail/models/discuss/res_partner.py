# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools import SQL
from odoo.addons.mail.tools.discuss import Store


class ResPartner(models.Model):
    _inherit = "res.partner"

    channel_ids = fields.Many2many(
        "discuss.channel",
        "discuss_channel_member",
        "partner_id",
        "channel_id",
        string="Channels",
        copy=False,
    )

    @api.readonly
    @api.model
    def search_for_channel_invite(self, search_term, channel_id=None, limit=30):
        """Returns partners matching search_term that can be invited to a channel.
        If the channel_id is specified, only partners that can actually be invited to the channel
        are returned (not already members, and in accordance to the channel configuration).
        """
        domain = expression.AND(
            [
                expression.OR(
                    [
                        [("name", "ilike", search_term)],
                        [("email", "ilike", search_term)],
                    ]
                ),
                [("active", "=", True)],
                [("user_ids", "!=", False)],
                [("user_ids.active", "=", True)],
                [("user_ids.share", "=", False)],
            ]
        )
        channel = self.env["discuss.channel"]
        if channel_id:
            channel = self.env["discuss.channel"].search([("id", "=", int(channel_id))])
            domain = expression.AND([domain, [("channel_ids", "not in", channel.id)]])
            if channel.group_public_id:
                domain = expression.AND(
                    [domain, [("user_ids.groups_id", "in", channel.group_public_id.id)]]
                )
        query = self._search(domain, limit=limit)
        # bypass lack of support for case insensitive order in search()
        query.order = SQL('LOWER(%s), "res_partner"."id"', self._field_to_sql(self._table, "name"))
        store = Store()
        self.env["res.partner"].browse(query)._search_for_channel_invite_to_store(store, channel)
        return {
            "count": self.env["res.partner"].search_count(domain),
            "data": store.get_result(),
        }

    def _search_for_channel_invite_to_store(self, store: Store, channel):
        store.add(self)

    @api.readonly
    @api.model
    def get_mention_suggestions_from_channel(self, channel_id, search, limit=8):
        """Return 'limit'-first partners' such that the name or email matches a 'search' string.
        Prioritize partners that are also (internal) users, and then extend the research to all partners.
        Only members of the given channel are returned.
        The return format is a list of partner data (as per returned by `_to_store()`).
        """
        channel = self.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            return []
        domain = expression.AND(
            [
                self._get_mention_suggestions_domain(search),
                [("channel_ids", "in", channel.id)],
            ]
        )
        extra_domain = expression.AND([
            [('user_ids', '!=', False)],
            [('user_ids.active', '=', True)],
            [('partner_share', '=', False)]
        ])
        if channel.group_public_id.id:
            extra_domain = expression.AND(
                [
                    extra_domain,
                    [("user_ids.groups_id", "in", channel.group_public_id.id)],
                ]
            )
        partners = self._search_mention_suggestions(domain, limit, extra_domain)
        members = self.env["discuss.channel.member"].search(
            [
                ("channel_id", "=", channel.id),
                ("partner_id", "in", partners.ids),
            ]
        )
        store = Store(members, fields={"channel": [], "persona": []})
        for p in partners:
            store.add(p,{
                "groups_id": [("ADD", next((group.id for group in p.user_ids.groups_id if group.id == channel.group_public_id.id), None))]
            })
        return store.get_result()
