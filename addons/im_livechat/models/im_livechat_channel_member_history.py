from odoo import api, models, fields
from odoo.exceptions import ValidationError


class ImLivechatChannelMemberHistory(models.Model):
    _name = "im_livechat.channel.member.history"
    _description = "Keep the channel member history"
    _rec_names_search = ["partner_id", "guest_id"]

    member_id = fields.Many2one("discuss.channel.member", index="btree_not_null")
    livechat_member_type = fields.Selection(
        [("agent", "Agent"), ("visitor", "Visitor"), ("bot", "Chatbot")],
        compute="_compute_member_fields",
        store=True,
    )
    channel_id = fields.Many2one(
        "discuss.channel",
        compute="_compute_member_fields",
        index=True,
        ondelete="cascade",
        store=True,
    )
    guest_id = fields.Many2one(
        "mail.guest", compute="_compute_member_fields", index="btree_not_null", store=True
    )
    partner_id = fields.Many2one(
        "res.partner", compute="_compute_member_fields", index="btree_not_null", store=True
    )
    chatbot_script_id = fields.Many2one(
        "chatbot.script", compute="_compute_member_fields", index="btree_not_null", store=True
    )
    agent_expertise_ids = fields.Many2many(
        "im_livechat.expertise", compute="_compute_member_fields", store=True
    )
    avatar_128 = fields.Binary(compute="_compute_avatar_128")

    _member_id_unique = models.Constraint(
        "UNIQUE(member_id)", "Members can only be linked to one history"
    )
    _channel_id_partner_id_unique = models.Constraint(
        "UNIQUE(channel_id, partner_id)",
        "One partner can only be linked to one history on a channel",
    )
    _channel_id_guest_id_unique = models.Constraint(
        "UNIQUE(channel_id, guest_id)",
        "One guest can only be linked to one history on a channel",
    )
    _partner_id_or_guest_id_constraint = models.Constraint(
        "CHECK(NOT (partner_id IS NOT NULL AND guest_id IS NOT NULL))",
        "History should either be linked to a partner or a guest but not both",
    )

    @api.constrains("channel_id")
    def _constraint_channel_id(self):
        # sudo: im_livechat.channel.member.history - skipping ACL for
        # constraint, more performant and no sensitive information is leaked.
        if failing_histories := self.sudo().filtered(
            lambda h: h.channel_id.channel_type != "livechat"
        ):
            raise ValidationError(
                self.env._(
                    "Cannot create history as it is only available for live chats: %(histories)s.",
                    histories=failing_histories.member_id.mapped("display_name")
                )
            )

    @api.depends("member_id")
    def _compute_member_fields(self):
        for history in self:
            history.channel_id = history.channel_id or history.member_id.channel_id
            history.guest_id = history.guest_id or history.member_id.guest_id
            history.partner_id = history.partner_id or history.member_id.partner_id
            history.livechat_member_type = (
                history.livechat_member_type or history.member_id.livechat_member_type
            )
            history.chatbot_script_id = history.chatbot_script_id or history.member_id.chatbot_script_id
            history.agent_expertise_ids = (
                history.agent_expertise_ids or history.member_id.agent_expertise_ids
            )

    @api.depends("livechat_member_type", "partner_id.name", "partner_id.display_name", "guest_id.name")
    def _compute_display_name(self):
        for history in self:
            name = history.partner_id.name or history.guest_id.name
            if history.partner_id and history.livechat_member_type == "visitor":
                name = history.partner_id.display_name
            history.display_name = name or self.env._("Unknown")

    @api.depends("partner_id.avatar_128", "guest_id.avatar_128")
    def _compute_avatar_128(self):
        for history in self:
            history.avatar_128 = history.partner_id.avatar_128 or history.guest_id.avatar_128
