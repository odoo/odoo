# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    calendar_event_ids = fields.One2many("calendar.event", "videocall_channel_id")

    def _should_invite_members_to_join_call(self):
        if self.calendar_event_ids:
            return False
        return super()._should_invite_members_to_join_call()
