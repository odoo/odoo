from odoo import fields, models

class DiscussChannelMember(models.Model):
    _inherit = 'discuss.channel.member'

    def _should_invite_members(self):
        if self.channel_id.calendar_event_id and fields.Datetime.now() < self.channel_id.calendar_event_id.start:
            return False
        return super()._should_invite_members()
