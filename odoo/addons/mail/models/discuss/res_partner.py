# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


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
        if channel_id:
            channel = self.env["discuss.channel"].search([("id", "=", int(channel_id))])
            domain = expression.AND([domain, [("channel_ids", "not in", channel.id)]])
            if channel.group_public_id:
                domain = expression.AND([domain, [("user_ids.groups_id", "in", channel.group_public_id.id)]])
        query = self.env["res.partner"]._search(domain, order="name, id")
        query.order = 'LOWER("res_partner"."name"), "res_partner"."id"'  # bypass lack of support for case insensitive order in search()
        query.limit = int(limit)
        return {
            "count": self.env["res.partner"].search_count(domain),
            "partners": list(self.env["res.partner"].browse(query).mail_partner_format().values()),
        }

    @api.model
    def get_mention_suggestions_from_channel(self, channel_id, search, limit=8):
        """Return 'limit'-first partners' such that the name or email matches a 'search' string.
        Prioritize partners that are also (internal) users, and then extend the research to all partners.
        Only members of the given channel are returned.
        The return format is a list of partner data (as per returned by `mail_partner_format()`).
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
        partners = self._search_mention_suggestions(domain, limit)
        member_by_partner = {
            member.partner_id: member
            for member in self.env["discuss.channel.member"].search(
                [
                    ("channel_id", "=", channel.id),
                    ("partner_id", "in", partners.ids),
                ]
            )
        }
        partners_format = partners.mail_partner_format()
        for partner in partners:
            partners_format.get(partner)["channelMembers"] = [
                    (
                        "ADD",
                        member_by_partner.get(partner)
                        ._discuss_channel_member_format(
                            fields={
                                "id": True,
                                "channel": {"id"},
                                "persona": {"partner": {"id"}},
                            }
                        )
                        .get(member_by_partner.get(partner)),
                    )
            ]
        return list(partners_format.values())
