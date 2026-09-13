from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.fields import Domain

from odoo.addons.mail.tools.discuss import Store


class DiscussChannelMember(models.Model):
    _inherit = "discuss.channel.member"

    livechat_member_history_ids = fields.One2many(
        comodel_name="im_livechat.channel.member.history",
        inverse_name="member_id",
    )
    livechat_member_type = fields.Selection(
        selection=[("agent", "Agent"), ("visitor", "Visitor"), ("bot", "Chatbot")],
        compute="_compute_livechat_member_type",
        inverse="_inverse_livechat_member_type",
        compute_sudo=True,
    )
    chatbot_script_id = fields.Many2one(
        comodel_name="chatbot.script",
        compute="_compute_chatbot_script_id",
        inverse="_inverse_chatbot_script_id",
        compute_sudo=True,
    )
    agent_expertise_ids = fields.Many2many(
        comodel_name="im_livechat.expertise",
        compute="_compute_agent_expertise_ids",
        inverse="_inverse_agent_expertise_ids",
        compute_sudo=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        members = super().create(vals_list)
        guest = self.env["mail.guest"]._get_guest_from_context()
        for member in members.filtered(
            lambda m: (
                m.channel_id.channel_type == "livechat" and not m.livechat_member_type
            )
        ):
            if (
                guest
                and member.is_self
                and guest in member.channel_id.livechat_customer_guest_ids
            ):
                member.sudo().livechat_member_type = "visitor"
                continue
            member.sudo().livechat_member_type = "agent"
        return members

    @api.depends("livechat_member_history_ids.livechat_member_type")
    def _compute_livechat_member_type(self):
        for member in self:
            member.livechat_member_type = (
                member.livechat_member_history_ids.livechat_member_type
            )

    @api.depends("livechat_member_history_ids.chatbot_script_id")
    def _compute_chatbot_script_id(self):
        for member in self:
            member.chatbot_script_id = (
                member.livechat_member_history_ids.chatbot_script_id
            )

    @api.depends("livechat_member_history_ids.agent_expertise_ids")
    def _compute_agent_expertise_ids(self):
        for member in self:
            member.agent_expertise_ids = (
                member.livechat_member_history_ids.agent_expertise_ids
            )

    def _create_or_update_history(self, values_by_member):
        members_without_history = self.filtered(
            lambda m: not m.livechat_member_history_ids
        )
        history_domain = Domain.OR(
            [
                [
                    ("channel_id", "=", member.channel_id.id),
                    ("partner_id", "=", member.partner_id.id)
                    if member.partner_id
                    else ("guest_id", "=", member.guest_id.id),
                ]
                for member in members_without_history
            ]
        )
        history_by_channel_persona = {}
        for history in self.env["im_livechat.channel.member.history"].search_fetch(
            history_domain, ["channel_id", "guest_id", "member_id", "partner_id"]
        ):
            persona = history.partner_id or history.guest_id
            history_by_channel_persona[history.channel_id, persona] = history
        to_create = members_without_history.filtered(
            lambda m: (
                (m.channel_id, m.partner_id or m.guest_id)
                not in history_by_channel_persona
            )
        )
        self.env["im_livechat.channel.member.history"].create(
            [
                {"member_id": member.id, **values_by_member[member]}
                for member in to_create
            ]
        )
        for member in self - to_create:
            persona = member.partner_id or member.guest_id
            history = (
                member.livechat_member_history_ids
                or history_by_channel_persona[member.channel_id, persona]
            )
            if history.member_id != member:
                values_by_member[member]["member_id"] = member.id
            if member in values_by_member:
                history.write(values_by_member[member])

    def _inverse_livechat_member_type(self):
        self.sudo()._create_or_update_history(
            {
                member: {"livechat_member_type": member.livechat_member_type}
                for member in self
            },
        )

    def _inverse_chatbot_script_id(self):
        self.sudo()._create_or_update_history(
            {
                member: {"chatbot_script_id": member.chatbot_script_id.id}
                for member in self
            }
        )

    def _inverse_agent_expertise_ids(self):
        self.sudo()._create_or_update_history(
            {
                member: {"agent_expertise_ids": member.agent_expertise_ids.ids}
                for member in self
            }
        )

    @api.autovacuum
    def _gc_unpin_livechat_sessions(self):
        members = self.env["discuss.channel.member"].search(
            [
                ("is_pinned", "=", True),
                ("last_seen_dt", "<=", datetime.now() - timedelta(days=1)),
                ("channel_id.channel_type", "=", "livechat"),
            ]
        )
        sessions_to_be_unpinned = members.filtered(
            lambda m: m.message_unread_counter == 0
        )
        sessions_to_be_unpinned.write({"unpin_dt": fields.Datetime.now()})
        sessions_to_be_unpinned.channel_id.livechat_end_dt = fields.Datetime.now()
        for member in sessions_to_be_unpinned:
            Store(bus_channel=member._bus_channel()).add(
                member.channel_id,
                {"close_chat_window": True, "livechat_end_dt": fields.Datetime.now()},
            ).bus_send()

    def _to_store_defaults(self, target):
        return super()._to_store_defaults(target) + [
            Store.Attr(
                "livechat_member_type",
                predicate=lambda member: member.channel_id.channel_type == "livechat",
            )
        ]

    def _get_store_partner_fields(self, field_specs):
        self.check_singleton()
        if self.channel_id.channel_type == "livechat":
            new_fields = [
                "active",
                "avatar_128",
                Store.One("country_id", ["code", "name"]),
                "im_status",
                "is_public",
                *self.env["res.partner"]._get_fields_store_livechat_username(),
            ]
            if self.livechat_member_type == "visitor":
                new_fields += ["offline_since", "email"]
            return new_fields
        return super()._get_store_partner_fields(field_specs)

    def _get_store_guest_fields(self, field_specs):
        self.check_singleton()
        if self.channel_id.channel_type == "livechat":
            return [
                "avatar_128",
                Store.One("country_id", ["code", "name"]),
                "im_status",
                "name",
                "offline_since",
            ]
        return super()._get_store_guest_fields(field_specs)

    def _get_domain_rtc_invite_members(self, *a, **kw):
        domain = super()._get_domain_rtc_invite_members(*a, **kw)
        if self.channel_id.channel_type == "livechat":
            domain &= Domain(
                "partner_id", "not in", self._get_excluded_rtc_members_partner_ids()
            )
        return domain

    def _get_excluded_rtc_members_partner_ids(self):
        chatbot = self.channel_id.chatbot_current_step_id.chatbot_script_id
        excluded_partner_ids = [chatbot.operator_partner_id.id] if chatbot else []
        return excluded_partner_ids

    def _get_html_link_title(self):
        if (
            self.channel_id.channel_type == "livechat"
            and self.partner_id.user_livechat_username
        ):
            return self.partner_id.user_livechat_username
        return super()._get_html_link_title()
