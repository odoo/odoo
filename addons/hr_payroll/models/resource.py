# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.osv.expression import AND
from odoo.tools import float_compare
from datetime import datetime

from odoo import models, fields, api
from odoo.addons.resource.models.resource_mixin import timezone_datetime

class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    hours_per_week = fields.Float(compute="_compute_hours_per_week", string="Hours per Week")
    full_time_required_hours = fields.Float(string="Fulltime Hours", help="Number of hours to work to be considered as fulltime.")
    is_fulltime = fields.Boolean(compute='_compute_is_fulltime', string="Is Full Time")

    # UI fields
    normal_attendance_ids = fields.One2many(
        'resource.calendar.attendance', 'calendar_id', 'Normal Working Time',
        domain=[('resource_id', '=', False)])

    extra_attendance_ids = fields.One2many(
        'resource.calendar.attendance', 'calendar_id', 'Employees Working Time',
        domain=[('resource_id', '!=', False)])

    @api.depends('normal_attendance_ids.hour_from', 'normal_attendance_ids.hour_to')
    def _compute_hours_per_week(self):
        for calendar in self:
            calendar.hours_per_week = sum((attendance.hour_to - attendance.hour_from) for attendance in calendar.normal_attendance_ids)

    def _compute_is_fulltime(self):
        for calendar in self:
            calendar.is_fulltime = not float_compare(calendar.full_time_required_hours, calendar.hours_per_week, 3)

    def _get_global_attendances(self):
        res = super(ResourceCalendar, self)._get_global_attendances()
        res |= self.normal_attendance_ids.filtered(lambda attendance: not attendance.date_from and not attendance.date_to)
        return res

    # Add a key on the api.onchange decorator
    @api.onchange('attendance_ids', 'normal_attendance_ids')
    def _onchange_hours_per_day(self):
        return super(ResourceCalendar, self)._onchange_hours_per_day()

    @api.multi
    def transfer_leaves_to(self, other_calendar, resources=None, from_date=None):
        """
            Transfer some resource.calendar.leaves from 'self' to another calendar 'other_calendar'.
            Transfered leaves linked to `resources` (or all if `resources` is None) and starting
            after 'from_date' (or today if None).
        """
        from_date = from_date or datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        domain = [
            ('calendar_id', 'in', self.ids),
            ('date_from', '>=', from_date),
        ]
        domain = AND([domain, [('resource_id', 'in', resources.ids)]]) if resources else domain

        self.env['resource.calendar.leaves'].search(domain).write({
            'calendar_id': other_calendar.id,
        })


class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'

    def _default_work_entry_type_id(self):
        return self.env.ref('hr_payroll.work_entry_type_attendance', raise_if_not_found=False)

    work_entry_type_id = fields.Many2one('hr.work.entry.type', 'Work Entry Type', default=_default_work_entry_type_id)


class ResourceCalendarLeave(models.Model):
    _inherit = 'resource.calendar.leaves'

    work_entry_type_id = fields.Many2one('hr.work.entry.type', 'Work Entry Type')


class ResourceMixin(models.AbstractModel):
    _inherit = "resource.mixin"

    def _get_work_entry_days_data(self, work_entry_type, from_datetime, to_datetime, calendar=None):
        """
            By default the resource calendar is used, but it can be
            changed using the `calendar` argument.

            Returns a dict {'days': n, 'hours': h} containing the number of leaves
            expressed as days and as hours.
        """
        resource = self.resource_id
        calendar = calendar or self.resource_calendar_id
        work_entry_type_ids = work_entry_type.ids
        if work_entry_type == self.env.ref('hr_payroll.work_entry_type_attendance'): # special case for global attendances
            work_entry_type_ids += [False]# no work_entry type = normal/global attendance
        domain = [('work_entry_type_id', 'in', work_entry_type_ids)]

        # naive datetimes are made explicit in UTC
        from_datetime = timezone_datetime(from_datetime)
        to_datetime = timezone_datetime(to_datetime)

        day_total = self._get_day_total(from_datetime, to_datetime, calendar, resource)
        # actual hours per day
        if work_entry_type.is_leave:
            intervals = calendar._attendance_intervals(from_datetime, to_datetime, resource) & calendar._leave_intervals(from_datetime, to_datetime, resource, domain) # use domain to only retrieve leaves of this type
        else:
            intervals = calendar._attendance_intervals(from_datetime, to_datetime, resource, domain) - calendar._leave_intervals(from_datetime, to_datetime, resource)

        return self._get_days_data(intervals, day_total)
