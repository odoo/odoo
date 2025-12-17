# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import api, models, fields
from odoo.fields import Domain
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.web.models.models import lazymapping


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
        stores = lazymapping(lambda channel: Store(bus_channel=channel))
        for history in members.livechat_member_history_ids:
            # sudo - visitor can access the channel member history of an accessible channel
            stores[history.channel_id].add(
                history.channel_id,
                lambda res, history=history: res.many(
                    "livechat_channel_member_history_ids",
                    "_store_member_history_fields",
                    mode="ADD",
                    value=history,
                    sudo=True,
                ),
            )
        for store in stores.values():
            store.bus_send()
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

    def _create_or_update_history(self, values_by_member):
        members_without_history = self.filtered(lambda m: not m.livechat_member_history_ids)
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
            lambda m: (m.channel_id, m.partner_id or m.guest_id) not in history_by_channel_persona
        )
        self.env["im_livechat.channel.member.history"].create(
            [{"member_id": member.id, **values_by_member[member]} for member in to_create]
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
        # sudo - im_livechat.channel.member: creating/updating history following
        # "livechat_member_type" modification is acceptable.
        self.sudo()._create_or_update_history(
            {member: {"livechat_member_type": member.livechat_member_type} for member in self},
        )

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
        sessions_to_be_unpinned.channel_id.livechat_end_dt = fields.Datetime.now()
        stores = lazymapping(lambda member: Store(bus_channel=member._bus_channel()))
        for member in sessions_to_be_unpinned:
            stores[member].add(member.channel_id, {"close_chat_window": True})
        for store in stores.values():
            store.bus_send()
        sessions_to_be_unpinned.unpin_dt = fields.Datetime.now()

    def _store_member_fields(self, res: Store.FieldList):
        super()._store_member_fields(res)
        res.attr(
            "livechat_member_type",
            predicate=lambda m: m.channel_id.channel_type == "livechat",
        )

    def _store_partner_dynamic_fields(self, partner_res: Store.FieldList):
        super()._store_partner_dynamic_fields(partner_res)
        if self.channel_id.channel_type != "livechat":
            return
        partner_res.clear()
        partner_res.attr("active")
        partner_res.one("country_id", ["code", "name"])
        partner_res.attr("is_public")
        partner_res.from_method("_store_avatar_fields")
        partner_res.from_method("_store_livechat_username_fields")
        partner_res.from_method("_store_mention_fields")
        if self.livechat_member_type == "visitor":
            partner_res.extend(["offline_since", "email"])
        if partner_res.is_for_internal_users():
            partner_res.from_method("_store_im_status_fields")

    def _store_guest_dynamic_fields(self, guest_res: Store.FieldList):
        super()._store_guest_dynamic_fields(guest_res)
        if self.channel_id.channel_type != "livechat":
            return
        guest_res.clear()
        guest_res.one("country_id", ["code", "name"])
        guest_res.attr("offline_since")
        guest_res.from_method("_store_guest_fields")

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
