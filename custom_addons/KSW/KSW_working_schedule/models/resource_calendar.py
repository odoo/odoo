from odoo import fields, models


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    is_temp_schedule = fields.Boolean(
        string='Is temporary Schedule',
        help='Indicates if this calendar is a temporary work schedule for employees',
    )

    calendar_group_ids = fields.Many2many(
        'resource.calendar.group',
        'resource_calendar_group_rel',
        'calendar_id',
        'group_id',
        string='Calendar Groups',
    )
