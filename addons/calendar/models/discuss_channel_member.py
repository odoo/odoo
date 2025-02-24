from odoo import fields, models


class DiscussChannelMember(models.Model):
    _inherit = "discuss.channel.member"

    def _should_invite_members_to_join_call(self):
        if self.channel_id.calendar_event_ids:
            return (
                super()._should_invite_members_to_join_call()
                and fields.Datetime.now() > self.channel_id.calendar_event_ids.start
            )
        return super()._should_invite_members_to_join_call()
