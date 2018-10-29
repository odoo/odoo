# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields
from odoo.osv.expression import AND, OR


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    # UI fields
    normal_attendance_ids = fields.One2many(
        'resource.calendar.attendance', 'calendar_id', 'Normal working Time',
        domain=[('resource_id', '=', False)])

    extra_attendance_ids = fields.One2many(
        'resource.calendar.attendance', 'calendar_id', 'Employees working Time',
        domain=[('resource_id', '!=', False)])


class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'

    def _default_benefit_type_id(self):
        return self.env.ref('hr_payroll.benefit_type_attendance', raise_if_not_found=False)

    benefit_type_id = fields.Many2one('hr.benefit.type', 'Benefit Type', default=_default_benefit_type_id)

class ResourceCalendarLeave(models.Model):
    _inherit = 'resource.calendar.leaves'
    benefit_type_id = fields.Many2one('hr.benefit.type', 'Benefit Type')


class ResourceMixin(models.AbstractModel):
    _inherit = "resource.mixin"

    def get_benefit_days_data(self, benefit_type, from_datetime, to_datetime, calendar=None):
        """
            By default the resource calendar is used, but it can be
            changed using the `calendar` argument.

            Returns a dict {'days': n, 'hours': h} containing the number of leaves
            expressed as days and as hours.
        """
        resource = self.resource_id
        calendar = calendar or self.resource_calendar_id
        benefit_type_ids = benefit_type.ids
        if benefit_type == self.env.ref('hr_payroll.benefit_type_attendance'): # special case for global attendances
            benefit_type_ids += [False]# no benefit type = normal/global attendance
        domain = [('benefit_type_id', 'in', benefit_type_ids)]

        # naive datetimes are made explicit in UTC
        from_datetime = self._timezone_datetime(from_datetime)
        to_datetime = self._timezone_datetime(to_datetime)

        day_total = self._get_day_total(from_datetime, to_datetime, calendar, resource)
        # actual hours per day
        if benefit_type.is_leave:
            intervals = calendar._attendance_intervals(from_datetime, to_datetime, resource) & calendar._leave_intervals(from_datetime, to_datetime, resource, domain) # use domain to only retrieve leaves of this type
        else:
            intervals = calendar._attendance_intervals(from_datetime, to_datetime, resource, domain) - calendar._leave_intervals(from_datetime, to_datetime, resource)

        return self._get_days_data(intervals, day_total)
