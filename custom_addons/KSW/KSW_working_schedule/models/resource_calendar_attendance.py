from odoo import fields, models

class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'

    calendar_id = fields.Many2one(required=False)

    calendar_group_id = fields.Many2one(
        'resource.calendar.group',
        string='Calendar Group',
        ondelete='cascade',
    )
