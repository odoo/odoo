import typing

from odoo import api, fields, models
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, email_normalize, single_email_re

from odoo.addons.mail.tools.discuss import Store, to_record_id

_debug = DebugLog(__name__)

if typing.TYPE_CHECKING:
    from .discuss_channel import DiscussChannel
    from .discuss_channel_member import DiscussChannelMember
    from .discuss_channel_rtc_session import DiscussChannelRtcSession


class ResPartner(models.Model):
    _inherit = "res.partner"

    channel_ids: DiscussChannel = fields.Many2many(
        comodel_name="discuss.channel",
        relation="discuss_channel_member",
        column1="partner_id",
        column2="channel_id",
        string="Channels",
        copy=False,
    )
    channel_member_ids: DiscussChannelMember = fields.One2many(
        comodel_name="discuss.channel.member",
        inverse_name="partner_id",
    )
    is_in_call = fields.Boolean(
        compute="_compute_is_in_call",
        groups="base.group_system",
    )
    rtc_session_ids: DiscussChannelRtcSession = fields.One2many(
        comodel_name="discuss.channel.rtc.session",
        inverse_name="partner_id",
    )

    @api.depends("rtc_session_ids")
    def _compute_is_in_call(self) -> None:
        for partner in self:
            partner.is_in_call = bool(partner.rtc_session_ids)

    @api.readonly
    @api.model
    def search_for_channel_invite(
        self, search_term: str, channel_id: int | None = None, limit: int = 30
    ) -> dict:
        store = Store()
        channel_invites = self._search_for_channel_invite(
            store, search_term, channel_id, limit
        )
        selectable_email = None
        email_already_sent = None
        if (
            channel_id
            and channel_invites["count"] == 0
            and single_email_re.match(search_term)
        ):
            email = email_normalize(search_term)
            channel = self.env["discuss.channel"].search_fetch(
                [("id", "=", to_record_id(channel_id))]
            )
            Member = self.env["discuss.channel.member"]
            member_domain = Domain(
                "channel_id", "=", channel.id
            ) & Member._member_email_domain([email])
            if (
                channel
                and channel._allow_invite_by_email()
                and not Member.search_count(member_domain, limit=1)
            ):
                selectable_email = email
                email_already_sent = (
                    self.env["mail.mail"]
                    .sudo()
                    .search_count(
                        [
                            ("email_to", "=", email),
                            ("model", "=", "discuss.channel"),
                            ("res_id", "=", channel.id),
                        ],
                        limit=1,
                    )
                    > 0
                )

        _debug.logic(
            "channel_invite_search",
            channel=channel_id,
            limit=limit,
            count=channel_invites["count"],
            selectable_email=bool(selectable_email),
            email_already_sent=email_already_sent,
        )
        return {
            **channel_invites,
            "email_already_sent": email_already_sent,
            "selectable_email": selectable_email,
            "store_data": store.get_result(),
        }

    @api.readonly
    @api.model
    def _search_for_channel_invite(
        self,
        store: Store,
        search_term: str,
        channel_id: int | None = None,
        limit: int = 30,
    ) -> dict:
        domain = Domain.AND(
            [
                Domain("name", "ilike", search_term)
                | Domain("email", "ilike", search_term),
                [("id", "!=", self.env.user.partner_id.id)],
                [("active", "=", True)],
                [("user_ids", "!=", False)],
                [("user_ids.active", "=", True)],
                [("user_ids.share", "=", False)],
            ]
        )
        channel = self.env["discuss.channel"]
        if channel_id:
            channel = self.env["discuss.channel"].search(
                [("id", "=", to_record_id(channel_id))]
            )
            domain &= Domain("channel_ids", "not in", channel.id)
            if channel.group_public_id:
                domain &= Domain(
                    "user_ids.all_group_ids", "in", channel.group_public_id.id
                )
        query = self._search(domain, limit=limit)
        query.order = SQL(
            'LOWER(%s), "res_partner"."id"', self._field_to_sql(self._table, "name")
        )
        selectable_partners = self.env["res.partner"].browse(query)
        selectable_partners._search_for_channel_invite_to_store(store, channel)
        return {
            "count": self.env["res.partner"].search_count(domain),
            "partner_ids": selectable_partners.ids,
        }

    def _search_for_channel_invite_to_store(
        self, store: Store, channel: DiscussChannel
    ) -> None:
        store.add(self)

    @api.readonly
    @api.model
    def get_mention_suggestions_from_channel(
        self, channel_id: int, search: str, limit: int = 8
    ) -> dict | list:
        channel = self.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            return []
        domain = Domain(
            [
                self._get_domain_mention_suggestions(search),
                ("channel_ids", "in", (channel.parent_channel_id | channel).ids),
            ]
        )
        extra_domain = Domain(
            [
                ("user_ids", "!=", False),
                ("user_ids.active", "=", True),
                ("partner_share", "=", False),
            ]
        )
        allowed_group = (channel.parent_channel_id or channel).group_public_id
        if allowed_group:
            extra_domain &= Domain("user_ids.all_group_ids", "in", allowed_group.id)
        partners = self._search_mention_suggestions(domain, limit, extra_domain)
        members_domain = [
            ("channel_id", "in", (channel.parent_channel_id | channel).ids),
            ("partner_id", "in", partners.ids),
        ]
        members = self.env["discuss.channel.member"].search(members_domain)
        _debug.logic(
            "mention_suggestions",
            channel=channel.id,
            limit=limit,
            group=allowed_group.id or None,
            partners=len(partners),
            members=len(members),
        )
        member_fields = [
            Store.One("channel_id", [], as_thread=True),
            *self.env["discuss.channel.member"]._to_store_persona([]),
        ]
        store = (
            Store()
            .add(members, member_fields)
            .add(partners, extra_fields=partners._get_fields_store_mention())
        )
        store.add(channel, "group_public_id")
        if allowed_group:
            for p in partners:
                store.add(
                    p,
                    {
                        "group_ids": [
                            ("ADD", (allowed_group & p.user_ids.all_group_ids).ids)
                        ]
                    },
                )
        try:
            roles = self.env["res.role"].search([("name", "ilike", search)], limit=8)
            store.add(roles, "name")
        except AccessError:
            pass
        return store.get_result()
