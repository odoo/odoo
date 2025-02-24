from odoo import fields, models


class DiscussChannelMember(models.Model):
    _inherit = "discuss.channel.member"

    def _should_invite_members_to_join_call(self):
        return (
            super()._should_invite_members_to_join_call()
            and self.channel_id.calendar_event_id
            and fields.Datetime.now() > self.channel_id.calendar_event_id.start
        )
