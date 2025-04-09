from odoo import api, models, fields
from odoo.exceptions import ValidationError


class ImLivechatChannelMemberHistory(models.Model):
    _name = "im_livechat.channel.member.history"
    _description = "Keep the channel member history"

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

    _member_id_unique = models.Constraint(
        "UNIQUE(member_id)", "Members can only be linked to one history"
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
