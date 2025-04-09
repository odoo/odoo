# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import api, models, fields
from odoo.osv import expression
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
                and guest in member.channel_id.channel_member_history_ids.guest_id
            ):
                # sudo - discuss.channel.member: setting livechat member type
                # after member creation is allowed.
                member.sudo().livechat_member_type = "visitor"
                continue
            member.sudo().livechat_member_type = "agent"
        return members

    def _compute_livechat_member_type(self):
        for member in self:
            member.livechat_member_type = member.livechat_member_history_ids.livechat_member_type

    def _inverse_livechat_member_type(self):
        # sudo - im_livechat.channel.member.history: creating history following
        # "livechat_member_type" modification is acceptable.
        self.env["im_livechat.channel.member.history"].sudo().create(
            [{"member_id": member.id} for member in self]
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
        # sudo: discuss.channel - reading livechat channel to check whether current member is a bot is allowed
        bot = self.channel_id.sudo().livechat_channel_id.rule_ids.chatbot_script_id.operator_partner_id
        return super()._to_store_defaults() + [
            Store.Attr(
                "is_bot",
                lambda member: member.partner_id in bot,
                predicate=lambda member: member.channel_id.channel_type == "livechat",
            )
        ]

    def _get_store_partner_fields(self, fields):
        self.ensure_one()
        if self.channel_id.channel_type == 'livechat':
            return [
                "active",
                "avatar_128",
                Store.One("country_id", ["code", "name"], rename="country"),
                "im_status",
                "is_public",
                "user_livechat_username",
            ]
        return super()._get_store_partner_fields(fields)

    def _get_rtc_invite_members_domain(self, *a, **kw):
        domain = super()._get_rtc_invite_members_domain(*a, **kw)
        chatbot = self.channel_id.chatbot_current_step_id.chatbot_script_id
        if self.channel_id.channel_type == "livechat" and chatbot:
            domain = expression.AND(
                [
                    domain,
                    [("partner_id", "!=", chatbot.operator_partner_id.id)],
                ]
            )
        return domain

    def _get_html_link_title(self):
        if self.channel_id.channel_type == "livechat" and self.partner_id.user_livechat_username:
            return self.partner_id.user_livechat_username
        return super()._get_html_link_title()
