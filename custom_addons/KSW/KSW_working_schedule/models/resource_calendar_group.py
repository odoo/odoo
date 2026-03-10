from odoo import fields, models


class ResourceCalendarGroup(models.Model):
    _name = 'resource.calendar.group'
    _description = 'Resource Calendar Group'

    name = fields.Char(string='Name', required=True)

    line_ids = fields.One2many(
        'resource.calendar.group.line',
        'calendar_group_id',
        string='Attendance Lines',
    )

    active = fields.Boolean(default=True)


class ResourceCalendarGroupLine(models.Model):
    _name = 'resource.calendar.group.line'
    _description = 'Resource Calendar Group Line'

    name = fields.Char(string='Description', required=True)
    calendar_group_id = fields.Many2one(
        'resource.calendar.group',
        string='Calendar Group',
        required=True,
        ondelete='cascade',
    )
    dayofweek = fields.Selection(
        [
            ('0', 'Monday'),
            ('1', 'Tuesday'),
            ('2', 'Wednesday'),
            ('3', 'Thursday'),
            ('4', 'Friday'),
            ('5', 'Saturday'),
            ('6', 'Sunday'),
        ],
        string='Day of Week',
        required=True, default='0',
    )
    day_period = fields.Selection(
        [
            ('morning', 'Morning'),
            ('afternoon', 'Afternoon'),
            ('full_day', 'Full Day'),
            ('break', 'Break'),
        ],
        string='Day Period',
        required=True,
        default='full_day',
    )
    hour_from = fields.Float(string='Work From', required=True, default=8.0)
    hour_to = fields.Float(string='Work To', required=True, default=16.5)
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    sequence = fields.Integer(default=10)