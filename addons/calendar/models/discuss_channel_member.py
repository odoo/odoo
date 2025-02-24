from odoo import fields, models

class DiscussChannelMember(models.Model):
    _inherit = 'discuss.channel.member'

    def _rtc_invite_members(self, member_ids=None):
        if self.channel_id.calendar_event_id and fields.Datetime.now() < self.channel_id.calendar_event_id.start:
            return
        return super()._rtc_invite_members(member_ids)
