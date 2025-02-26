from odoo import fields, models

class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    calendar_event_id = fields.One2many('calendar.event', 'videocall_channel_id')
