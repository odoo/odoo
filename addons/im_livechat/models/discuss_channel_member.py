# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import api, models, fields
from odoo.fields import Domain
from odoo.addons.mail.tools.discuss import Store


class DiscussChannelMember(models.Model):
    _inherit = 'discuss.channel.member'

    livechat_member_history_ids = fields.One2many("im_livechat.channel.member.history", "member_id")
    livechat_member_type = fields.Selection(
        [("agent", "Agent"), ("visitor", "Visitor"), ("bot", "Chatbot")],
        compute="_compute_livechat_member_type",
        # sudo - reading the history of a member the user has access to is acceptable.
        compute_sudo=True,
        inverse="_inverse_livechat_member_type",
    )
    chatbot_script_id = fields.Many2one(
        "chatbot.script",
        compute="_compute_chatbot_script_id",
        inverse="_inverse_chatbot_script_id",
        compute_sudo=True,
    )
    agent_expertise_ids = fields.Many2many(
        "im_livechat.expertise",
        compute="_compute_agent_expertise_ids",
        # sudo - reading the history of a member the user has access to is acceptable.
        compute_sudo=True,
        inverse="_inverse_agent_expertise_ids",
    )

    @api.model_create_multi
    def create(self, vals_list):
        members = super().create(vals_list)
        guest = self.env["mail.guest"]._get_guest_from_context()
        for member in members.filtered(
            lambda m: m.channel_id.channel_type == "livechat" and not m.livechat_member_type
        ):
            # After login, the guest cookie is still available, allowing us to
            # reconcile the user with their previous guest member.
            if (
                guest
                and member.is_self
                and guest in member.channel_id.livechat_customer_guest_ids
            ):
                # sudo - discuss.channel.member: setting livechat member type
                # after member creation is allowed.
                member.sudo().livechat_member_type = "visitor"
                continue
            member.sudo().livechat_member_type = "agent"
        return members

    @api.depends("livechat_member_history_ids.livechat_member_type")
    def _compute_livechat_member_type(self):
        for member in self:
            member.livechat_member_type = member.livechat_member_history_ids.livechat_member_type

    @api.depends("livechat_member_history_ids.chatbot_script_id")
    def _compute_chatbot_script_id(self):
        for member in self:
            member.chatbot_script_id = member.livechat_member_history_ids.chatbot_script_id

    @api.depends("livechat_member_history_ids.agent_expertise_ids")
    def _compute_agent_expertise_ids(self):
        for member in self:
            member.agent_expertise_ids = member.livechat_member_history_ids.agent_expertise_ids

    def _create_or_update_history(self, values_by_member=None):
        if not values_by_member:
            values_by_member = {}
        member_without_history = self.filtered(lambda m: not m.livechat_member_history_ids)
        self.env["im_livechat.channel.member.history"].create(
            [
                {"member_id": member.id, **values_by_member.get(member, {})}
                for member in member_without_history
            ]
        )
        for member in (self - member_without_history):
            if member in values_by_member:
                member.livechat_member_history_ids.update(values_by_member[member])

    def _inverse_livechat_member_type(self):
        # sudo - im_livechat.channel.member: creating/updating history following
        # "livechat_member_type" modification is acceptable.
        self.sudo()._create_or_update_history()

    def _inverse_chatbot_script_id(self):
        # sudo - im_livechat.channel.member: creating/updating history following
        # "chatbot_script_id" modification is acceptable.
        self.sudo()._create_or_update_history(
            {member: {"chatbot_script_id": member.chatbot_script_id.id} for member in self}
        )

    def _inverse_agent_expertise_ids(self):
        # sudo - im_livechat.channel.member.history: creating/udpating history following
        # "agent_expetise_ids" modification is acceptable.
        self.sudo()._create_or_update_history(
            {member: {"agent_expertise_ids": member.agent_expertise_ids.ids} for member in self}
        )

    @api.autovacuum
    def _gc_unpin_livechat_sessions(self):
        """ Unpin read livechat sessions with no activity for at least one day to
            clean the operator's interface """
        members = self.env['discuss.channel.member'].search([
            ('is_pinned', '=', True),
            ('last_seen_dt', '<=', datetime.now() - timedelta(days=1)),
            ('channel_id.channel_type', '=', 'livechat'),
        ])
        sessions_to_be_unpinned = members.filtered(lambda m: m.message_unread_counter == 0)
        sessions_to_be_unpinned.write({'unpin_dt': fields.Datetime.now()})
        sessions_to_be_unpinned.channel_id.livechat_active = False
        for member in sessions_to_be_unpinned:
            member._bus_send_store(
                member.channel_id, {"close_chat_window": True, "is_pinned": False, "livechat_active": False}
            )

    def _to_store_defaults(self):
        bot = self._get_bot_partner_ids()
        return super()._to_store_defaults() + [
            Store.Attr(
                "livechat_member_type",
                predicate=lambda member: member.channel_id.channel_type == "livechat",
            )
        ]

    def _get_bot_partner_ids(self):
        # sudo: discuss.channel - reading livechat channel to check whether current member is a bot is allowed
        return self.channel_id.sudo().livechat_channel_id.rule_ids.mapped('chatbot_script_id.operator_partner_id')

    def _get_store_partner_fields(self, fields):
        self.ensure_one()
        if self.channel_id.channel_type == 'livechat':
            new_fields = [
                "active",
                "avatar_128",
                Store.One("country_id", ["code", "name"]),
                "im_status",
                "is_public",
                *self.env["res.partner"]._get_store_livechat_username_fields(),
            ]
            if self.livechat_member_type == "visitor":
                new_fields += ["offline_since"]
            return new_fields
        return super()._get_store_partner_fields(fields)

    def _get_store_guest_fields(self, fields):
        self.ensure_one()
        if self.channel_id.channel_type == 'livechat':
            return [
                "avatar_128",
                Store.One("country_id", ["code", "name"]),
                "im_status",
                "name",
                "offline_since",
            ]
        return super()._get_store_guest_fields(fields)

    def _get_rtc_invite_members_domain(self, *a, **kw):
        domain = super()._get_rtc_invite_members_domain(*a, **kw)
        if self.channel_id.channel_type == "livechat":
            domain &= Domain("partner_id", "not in", self._get_excluded_rtc_members_partner_ids())
        return domain

    def _get_excluded_rtc_members_partner_ids(self):
        chatbot = self.channel_id.chatbot_current_step_id.chatbot_script_id
        excluded_partner_ids = [chatbot.operator_partner_id.id] if chatbot else []
        return excluded_partner_ids

    def _get_html_link_title(self):
        if self.channel_id.channel_type == "livechat" and self.partner_id.user_livechat_username:
            return self.partner_id.user_livechat_username
        return super()._get_html_link_title()
