# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math

from odoo import api, fields, models, _


class ResourceCalendarAttendance(models.Model):
    _name = "resource.calendar.attendance"
    _description = "Work Detail"
    _order = 'sequence, week_type, dayofweek, hour_from'

    name = fields.Char(required=True)
    dayofweek = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
        ], 'Day of Week', required=True, index=True, default='0')
    date_from = fields.Date(string='Starting Date')
    date_to = fields.Date(string='End Date')
    hour_from = fields.Float(string='Work from', required=True, index=True,
        help="Start and End time of working.\n"
             "A specific value of 24:00 is interpreted as 23:59:59.999999.")
    hour_to = fields.Float(string='Work to', required=True)
    # For the hour duration, the compute function is used to compute the value
    # unambiguously, while the duration in days is computed for the default
    # value based on the day_period but can be manually overridden.
    duration_hours = fields.Float(compute='_compute_duration_hours', string='Duration (hours)')
    duration_days = fields.Float(compute='_compute_duration_days', string='Duration (days)', store=True, readonly=False)
    calendar_id = fields.Many2one("resource.calendar", string="Resource's Calendar", required=True, ondelete='cascade')
    day_period = fields.Selection([
        ('morning', 'Morning'),
        ('lunch', 'Break'),
        ('afternoon', 'Afternoon')], required=True, default='morning')
    resource_id = fields.Many2one('resource.resource', 'Resource')
    week_type = fields.Selection([
        ('1', 'Second'),
        ('0', 'First')
        ], 'Week Number', default=False)
    two_weeks_calendar = fields.Boolean("Calendar in 2 weeks mode", related='calendar_id.two_weeks_calendar')
    display_type = fields.Selection([
        ('line_section', "Section")], default=False, help="Technical field for UX purpose.")
    sequence = fields.Integer(default=10,
        help="Gives the sequence of this line when displaying the resource calendar.")

    @api.onchange('hour_from', 'hour_to')
    def _onchange_hours(self):
        # avoid negative or after midnight
        self.hour_from = min(self.hour_from, 23.99)
        self.hour_from = max(self.hour_from, 0.0)
        self.hour_to = min(self.hour_to, 24)
        self.hour_to = max(self.hour_to, 0.0)

        # avoid wrong order
        self.hour_to = max(self.hour_to, self.hour_from)

    @api.model
    def get_week_type(self, date):
        # week_type is defined by
        #  * counting the number of days from January 1 of year 1
        #    (extrapolated to dates prior to the first adoption of the Gregorian calendar)
        #  * converted to week numbers and then the parity of this number is asserted.
        # It ensures that an even week number always follows an odd week number. With classical week number,
        # some years have 53 weeks. Therefore, two consecutive odd week number follow each other (53 --> 1).
        return int(math.floor((date.toordinal() - 1) / 7) % 2)

    @api.depends('hour_from', 'hour_to')
    def _compute_duration_hours(self):
        for attendance in self:
            attendance.duration_hours = (attendance.hour_to - attendance.hour_from) if attendance.day_period != 'lunch' else 0

    @api.depends('day_period', 'duration_hours')
    def _compute_duration_days(self):
        for attendance in self:
            if attendance.day_period == 'lunch':
                attendance.duration_days = 0
            else:
                attendance.duration_days = 0.5 if attendance.duration_hours <= attendance.calendar_id.hours_per_day * 3 / 4 else 1

    @api.depends('week_type')
    def _compute_display_name(self):
        super()._compute_display_name()
        this_week_type = str(self.get_week_type(fields.Date.context_today(self)))
        section_names = {'0': _('First week'), '1': _('Second week')}
        section_info = {True: _('this week'), False: _('other week')}
        for record in self.filtered(lambda l: l.display_type == 'line_section'):
            section_name = f"{section_names[record.week_type]} ({section_info[this_week_type == record.week_type]})"
            record.display_name = section_name

    def _copy_attendance_vals(self):
        self.ensure_one()
        return {
            'name': self.name,
            'dayofweek': self.dayofweek,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'hour_from': self.hour_from,
            'hour_to': self.hour_to,
            'day_period': self.day_period,
            'week_type': self.week_type,
            'display_type': self.display_type,
            'sequence': self.sequence,
        }
