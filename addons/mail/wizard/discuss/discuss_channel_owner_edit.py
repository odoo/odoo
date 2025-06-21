# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class DiscussChannelOwnerEdit(models.TransientModel):
    _name = 'discuss.channel.owner.edit'
    _description = 'Edit Channel Owner'

    channel_id = fields.Many2one('discuss.channel', string="Channel", required=True)
    channel_owner_candidate_id = fields.Many2one(
        'res.partner',
        string="Channel Owner Candidate",
        required=True,
        store=True,
    )
    channel_partner_ids = fields.Many2many(
        'res.partner',
        compute='_compute_channel_partner_ids',
    )

    @api.depends('channel_id.channel_partner_ids')
    def _compute_channel_partner_ids(self):
        for record in self:
            record.channel_partner_ids = record.channel_id.channel_partner_ids.filtered(
                lambda partner: partner != self.env.user.partner_id,
            )

    def transfer_owner(self):
        self.ensure_one()
        member = self.channel_id.channel_member_ids.filtered(
            lambda member: member.partner_id == self.env.user.partner_id,
        )
        # sudo: discuss.channel.member - writing channel role related to a member is considered acceptable
        member.sudo().write({"channel_role": None})
        member.flush_recordset()
        # sudo: discuss.channel.member - writing channel role related to a member is considered acceptable
        self.channel_id.channel_member_ids.filtered(
            lambda member: member.partner_id == self.channel_owner_candidate_id,
        ).sudo().write({"channel_role": "owner"})
        # check if the member is unlink based on the context
        if self.env.context.get('unlink_after_transfer'):
            # sudo: discuss.channel.member - unlinking a member is considered acceptable based on the context
            member.sudo().unlink()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
            "type": "success",
            "message": self.env._("Channel owner has been transferred."),
            "sticky": False,
            "next": {"type": "ir.actions.act_window_close"},
            },
        }
