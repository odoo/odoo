# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class HrLeaveAttendanceLine(models.Model):
    _name = 'hr.leave.attendance.line'
    _description = 'Leave Attendance Issue Hours'
    _order = 'date, hour_from'

    leave_id = fields.Many2one(
        'hr.leave',
        string='Leave Request',
        required=True,
        ondelete='cascade',
    )
    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Attendance Record',
        required=True,
        ondelete='cascade',
    )
    issue_type = fields.Selection([
        ('late', 'Late'),
        ('early_leave', 'Early Leave'),
    ], string='Issue Type', required=True)
    date = fields.Date(
        string='Date',
        compute='_compute_date',
        store=True,
    )
    hour_from = fields.Float(string='From')
    hour_to = fields.Float(string='To')
    duration_minutes = fields.Float(
        string='Duration (min)',
        compute='_compute_duration_minutes',
        store=True,
    )
    accepted_minutes = fields.Float(
        string='Accepted (min)',
        help='The approved portion of this issue in minutes. Cannot exceed the total duration.',
    )

    @api.depends('attendance_id.check_in')
    def _compute_date(self):
        for line in self:
            if line.attendance_id and line.attendance_id.check_in:
                line.date = line.attendance_id.check_in.date()
            else:
                line.date = False

    @api.depends('hour_from', 'hour_to')
    def _compute_duration_minutes(self):
        for line in self:
            line.duration_minutes = round((line.hour_to - line.hour_from) * 60.0, 1)

    @api.constrains('accepted_minutes', 'duration_minutes')
    def _check_accepted_minutes(self):
        for line in self:
            if line.accepted_minutes < 0:
                raise ValidationError(
                    _('Accepted minutes cannot be negative.')
                )
            if line.accepted_minutes > line.duration_minutes:
                raise ValidationError(
                    _('Accepted minutes (%(accepted)s) cannot exceed the total duration (%(total)s).',
                      accepted=line.accepted_minutes,
                      total=line.duration_minutes)
                )

    @api.onchange('accepted_minutes')
    def _onchange_accepted_minutes(self):
        """Clamp accepted_minutes so it never exceeds duration or goes negative."""
        if self.accepted_minutes < 0:
            self.accepted_minutes = 0
        duration = round((self.hour_to - self.hour_from) * 60.0, 1)
        if self.accepted_minutes > duration:
            self.accepted_minutes = duration
            return {
                'warning': {
                    'title': _('Value Adjusted'),
                    'message': _('Accepted minutes cannot exceed the total duration (%(total)s min).', total=duration),
                }
            }





