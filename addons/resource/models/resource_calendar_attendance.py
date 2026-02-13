# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math

from odoo import api, fields, models


class ResourceCalendarAttendance(models.Model):
    _name = 'resource.calendar.attendance'
    _description = "Work Detail"
    _order = 'sequence, week_type, dayofweek, hour_from'

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
    # For the hour duration, the compute function is used to compute the value
    # unambiguously, while the duration in days is computed for the default
    # value but can be manually overridden.
    duration_hours = fields.Float(compute='_compute_duration_hours', string='Hours', store=True, readonly=False)
    calendar_id = fields.Many2one("resource.calendar", string="Resource's Calendar", required=True, index=True, ondelete='cascade')
    duration_based = fields.Boolean(compute='_compute_duration_based', store=True)
    day_period = fields.Selection([
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('full_day', 'Full Day')], store=True, compute='_compute_day_period')
    week_type = fields.Selection([
        ('1', 'Second'),
        ('0', 'First'),
        ], 'Week Number', default=False)
    two_weeks_calendar = fields.Boolean("Calendar in 2 weeks mode", related='calendar_id.two_weeks_calendar')
    sequence = fields.Integer(default=10,
        help="Gives the sequence of this line when displaying the resource calendar.")

    @api.onchange('hour_from')
    def _onchange_hour_from(self):
        # avoid negative or after midnight
        self.hour_from = min(self.hour_from, 23.99)
        self.hour_from = max(self.hour_from, 0.0)

    @api.onchange('hour_to')
    def _onchange_hour_to(self):
        # avoid negative or after midnight
        self.hour_to = min(self.hour_to, 24)
        self.hour_to = max(self.hour_to, 0.0)

        if self.hour_from and not self.hour_to:
            self.hour_from = 0.0

        # avoid wrong order
        self.hour_to = max(self.hour_to, self.hour_from)

    @api.onchange('duration_hours')
    def _onchange_duration_hours(self):
        self.duration_hours = min(self.duration_hours, 24)
        if self.hour_from or self.hour_to:
            if self.hour_from + self.duration_hours > 24:
                self.hour_from = 24 - self.duration_hours
                self.hour_to = 24
            else:
                self.hour_to = self.hour_from + self.duration_hours

    @api.depends('hour_from', 'hour_to')
    def _compute_duration_based(self):
        for attendance in self:
            attendance.duration_based = not attendance.hour_from and not attendance.hour_to

    @api.depends('duration_hours', 'hour_from', 'hour_to')
    def _compute_day_period(self):
        for attendance in self:
            if attendance.duration_hours > (0.75 * attendance.calendar_id.hours_per_day) or (not attendance.hour_from and not attendance.hour_to):
                attendance.day_period = 'full_day'
            elif attendance.hour_from and attendance.hour_to:
                if attendance.hour_from > 12 or (12 - attendance.hour_from <= attendance.hour_to - 12):
                    attendance.day_period = 'afternoon'
                else:
                    attendance.day_period = 'morning'
            else:
                attendance.day_period = 'morning'

    @api.depends('hour_from', 'hour_to')
    def _compute_duration_hours(self):
        for attendance in self.filtered(lambda att: att.hour_from or att.hour_to):
            attendance.duration_hours = max(0, attendance.hour_to - attendance.hour_from)

    @api.depends('week_type')
    def _compute_display_name(self):
        super()._compute_display_name()
        section_names = {'0': self.env._('First week'), '1': self.env._('Second week')}
        dayofweek_selection = dict(self._fields['dayofweek']._description_selection(self.env))
        day_period_selection = dict(self._fields['day_period']._description_selection(self.env))
        for record in self:
            record.display_name = f"{dayofweek_selection[record.dayofweek]} ({day_period_selection[record.day_period]})"
            if record.two_weeks_calendar:
                record.display_name = section_names[record.weektype] + ' - ' + record.display_name

    @api.model
    def get_week_type(self, date):
        # week_type is defined by
        #  * counting the number of days from January 1 of year 1
        #    (extrapolated to dates prior to the first adoption of the Gregorian calendar)
        #  * converted to week numbers and then the parity of this number is asserted.
        # It ensures that an even week number always follows an odd week number. With classical week number,
        # some years have 53 weeks. Therefore, two consecutive odd week number follow each other (53 --> 1).
        return int(math.floor((date.toordinal() - 1) / 7) % 2)

    def _copy_attendance_vals(self):
        self.ensure_one()
        return {
            'dayofweek': self.dayofweek,
            'duration_hours': self.duration_hours,
            'hour_from': self.hour_from,
            'hour_to': self.hour_to,
            'week_type': self.week_type,
            'sequence': self.sequence,
        }

    def _is_work_period(self):
        return True
