# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ResourceCalendarAttendance(models.Model):
    _name = 'resource.calendar.attendance'
    _description = "Work Detail"
    _order = 'dayofweek, hour_from'

    dayofweek = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
        ], 'Day of Week', required=True, index=True, default='0')
    hour_from = fields.Float(string='Work from', default=0, required=True, index=True,
        help="Start and End time of working.\n"
             "A specific value of 24:00 is interpreted as 23:59:59.999999.")
    hour_to = fields.Float(string='Work to', default=0, required=True)
    break_hours = fields.Float(string="Break", default=0)
    # For the hour duration, the compute function is used to compute the value
    # unambiguously, while the duration in days is computed for the default
    # value based on the day_period but can be manually overridden.
    duration_hours = fields.Float(compute='_compute_duration_hours', inverse='_inverse_duration_hours', string='Duration (hours)', store=True, readonly=False)
    calendar_id = fields.Many2one("resource.calendar", string="Resource's Calendar", required=True, index=True, ondelete='cascade')
    display_type = fields.Selection([
        ('line_section', "Section")], default=False, help="Technical field for UX purpose.")

    @api.onchange('hour_from', 'hour_to')
    def _onchange_hours(self):
        # avoid negative or after midnight
        self.hour_from = min(self.hour_from, 23.99)
        self.hour_from = max(self.hour_from, 0.0)
        self.hour_to = min(self.hour_to, 24)
        self.hour_to = max(self.hour_to, 0.0)

        # avoid wrong order
        self.hour_to = max(self.hour_to, self.hour_from)

    @api.depends('hour_from', 'hour_to')
    def _compute_duration_hours(self):
        for attendance in self.filtered('hour_to'):
            attendance.duration_hours = (attendance.hour_to - attendance.hour_from) if attendance.day_period != 'lunch' else 0

    def _inverse_duration_hours(self):
        for attendance in self:
            if attendance.day_period == 'full_day':
                period_duration = attendance.duration_hours / 2
                attendance.hour_to = 12 + period_duration
                attendance.hour_from = 12 - period_duration
            elif attendance.day_period == 'morning':
                attendance.hour_to = 12
                attendance.hour_from = 12 - attendance.duration_hours
            elif attendance.day_period == 'afternoon':
                attendance.hour_to = 12 + attendance.duration_hours
                attendance.hour_from = 12

    def _copy_attendance_vals(self):
        self.ensure_one()
        return {
            'dayofweek': self.dayofweek,
            'hour_from': self.hour_from,
            'hour_to': self.hour_to,
            'day_period': self.day_period,
            'display_type': self.display_type,
        }

    def _is_work_period(self):
        return self.day_period != 'lunch' and not self.display_type
