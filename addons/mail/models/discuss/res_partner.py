# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import email_normalize, single_email_re, SQL
from odoo.addons.mail.tools.discuss import Store
from odoo.exceptions import AccessError


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
    channel_member_ids = fields.One2many("discuss.channel.member", "partner_id")
    is_in_call = fields.Boolean(compute="_compute_is_in_call", groups="base.group_system")
    rtc_session_ids = fields.One2many("discuss.channel.rtc.session", "partner_id")

    @api.depends("rtc_session_ids")
    def _compute_is_in_call(self):
        for partner in self:
            partner.is_in_call = bool(partner.rtc_session_ids)

    @api.readonly
    @api.model
    def search_for_channel_invite(self, search_term, channel_id=None, limit=30):
        """Returns partners matching search_term that can be invited to a channel.

        - If `channel_id` is specified, only partners that can actually be invited to the channel
          are returned (not already members, and in accordance to the channel configuration).

        - If no matching partners are found and the search term is a valid email address,
          then the method may return `selectable_email` as a fallback direct email invite, provided that
          the channel allows invites by email.

        """
        store = Store()
        channel_invites = self._search_for_channel_invite(store, search_term, channel_id, limit)
        selectable_email = None
        email_already_sent = None
        if channel_invites["count"] == 0 and single_email_re.match(search_term):
            email = email_normalize(search_term)
            channel = self.env["discuss.channel"].search_fetch([("id", "=", int(channel_id))])
            member_domain = Domain("channel_id", "=", channel.id)
            member_domain &= Domain("guest_id.email", "=", email) | Domain(
                "partner_id.email", "=", email
            )
            if channel._allow_invite_by_email() and not self.env[
                "discuss.channel.member"
            ].search_count(member_domain):
                selectable_email = email
                # sudo - mail.mail: checking mail records to determine if an email was already sent is acceptable.
                email_already_sent = (
                    self.env["mail.mail"]
                    .sudo()
                    .search_count(
                        [
                            ("email_to", "=", email),
                            ("model", "=", "discuss.channel"),
                            ("res_id", "=", channel.id),
                        ]
                    )
                    > 0
                )

        return {
            **channel_invites,
            "email_already_sent": email_already_sent,
            "selectable_email": selectable_email,
            "store_data": store.get_result(),
        }

    @api.readonly
    @api.model
    def _search_for_channel_invite(self, store: Store, search_term, channel_id=None, limit=30):
        domain = Domain.AND(
            [
                Domain("name", "ilike", search_term) | Domain("email", "ilike", search_term),
                [('id', '!=', self.env.user.partner_id.id)],
                [("active", "=", True)],
                [("user_ids", "!=", False)],
                [("user_ids.active", "=", True)],
                [("user_ids.share", "=", False)],
            ]
        )
        channel = self.env["discuss.channel"]
        if channel_id:
            channel = self.env["discuss.channel"].search([("id", "=", int(channel_id))])
            domain &= Domain("channel_ids", "not in", channel.id)
            if channel.group_public_id:
                domain &= Domain("user_ids.all_group_ids", "in", channel.group_public_id.id)
        query = self._search(domain, limit=limit)
        # bypass lack of support for case insensitive order in search()
        query.order = SQL('LOWER(%s), "res_partner"."id"', self._field_to_sql(self._table, "name"))
        selectable_partners = self.env["res.partner"].browse(query)
        selectable_partners._search_for_channel_invite_to_store(store, channel)
        return {
            "count": self.env["res.partner"].search_count(domain),
            "partner_ids": selectable_partners.ids,
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
        domain = self._get_mention_suggestions_domain(search) & Domain("channel_ids", "in", channel.id)
        extra_domain = Domain([
            ('user_ids', '!=', False),
            ('user_ids.active', '=', True),
            ('partner_share', '=', False),
        ])
        allowed_group = (channel.parent_channel_id or channel).group_public_id
        if allowed_group:
            extra_domain &= Domain("user_ids.all_group_ids", "in", allowed_group.id)
        partners = self._search_mention_suggestions(domain, limit, extra_domain)
        members_domain = [("channel_id", "=", channel.id), ("partner_id", "in", partners.ids)]
        members = self.env["discuss.channel.member"].search(members_domain)
        member_fields = [
            Store.One("channel_id", [], as_thread=True),
            *self.env["discuss.channel.member"]._to_store_persona([]),
        ]
        store = (
            Store()
            .add(members, member_fields)
            .add(partners, extra_fields=partners._get_store_mention_fields())
        )
        store.add(channel, "group_public_id")
        if allowed_group:
            for p in partners:
                store.add(p, {"group_ids": [("ADD", (allowed_group & p.user_ids.all_group_ids).ids)]})
        try:
            roles = self.env["res.role"].search([("name", "ilike", search)], limit=8)
            store.add(roles, "name")
        except AccessError:
            pass
        return store.get_result()
