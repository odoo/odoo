from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..tools import debug_log as dbg


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    subscription_department_ids = fields.Many2many(
        comodel_name="hr.department",
        string="HR Departments",
        help="Automatically subscribe members of those departments to the channel.",
    )

    @api.constrains("subscription_department_ids")
    def _check_department_subscription_requires_channel(self):
        failing_channels = self.sudo().filtered(
            lambda channel: (
                channel.channel_type != "channel"
                and channel.subscription_department_ids
            )
        )
        if failing_channels:
            raise ValidationError(
                self.env._(
                    "For %(channels)s, channel_type should be 'channel' to have the department auto-subscription.",
                    channels=", ".join([ch.name for ch in failing_channels]),
                )
            )

    def _subscribe_users_automatically_get_members(self):
        new_members = super()._subscribe_users_automatically_get_members()
        for channel in self:
            department_partners = channel.subscription_department_ids.sudo().member_ids.user_id.partner_id.filtered(
                lambda p: p.active
            )
            new_members[channel.id] = list(
                set(new_members[channel.id])
                | set((department_partners - channel.channel_partner_ids).ids)
            )
            dbg.pipeline.debug(
                "[channel:%s] departments %s -> %d member partner(s), %d new",
                channel.id,
                channel.subscription_department_ids.ids,
                len(department_partners),
                len(department_partners - channel.channel_partner_ids),
            )
        return new_members

    def write(self, vals):
        res = super().write(vals)
        if vals.get("subscription_department_ids"):
            dbg.pipeline.debug(
                "discuss.channel.write on %s: subscription departments changed, "
                "resubscribing",
                dbg.rec(self),
            )
            self._subscribe_users_automatically()
        return res
