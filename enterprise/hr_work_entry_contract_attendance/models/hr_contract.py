# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import pytz

from pytz import timezone
from datetime import timedelta

from odoo import fields, models
from odoo.addons.hr_work_entry_contract.models.hr_work_intervals import WorkIntervals
from odoo.addons.resource.models.utils import Intervals

class HrContract(models.Model):
    _inherit = 'hr.contract'

    work_entry_source = fields.Selection(
        selection_add=[('attendance', 'Attendances')],
        ondelete={'attendance': 'set default'},
    )

    def _get_more_vals_attendance_interval(self, interval):
        result = super()._get_more_vals_attendance_interval(interval)
        if interval[2]._name == 'hr.attendance':
            result.append(('attendance_id', interval[2].id))
        return result

    def _get_attendance_intervals(self, start_dt, end_dt):
        ##################################
        #   ATTENDANCE BASED CONTRACTS   #
        ##################################
        attendance_based_contracts = self.filtered(lambda c: c.work_entry_source == 'attendance')
        search_domain = [
            ('employee_id', 'in', attendance_based_contracts.employee_id.ids),
            ('check_in', '<', end_dt),
            ('check_out', '>', start_dt), # We ignore attendances which don't have a check_out
        ]
        resource_ids = attendance_based_contracts.employee_id.resource_id.ids
        attendances = self.env['hr.attendance'].sudo().search(search_domain) if attendance_based_contracts\
            else self.env['hr.attendance']
        intervals = defaultdict(list)
        for attendance in attendances:
            emp_cal = attendance._get_employee_calendar()
            resource = attendance.employee_id.resource_id
            tz = timezone(emp_cal.tz or resource.tz)    # refer to resource's tz if fully flexible resource (calendar is False)
            check_in_tz = attendance.check_in.astimezone(tz)
            check_out_tz = attendance.check_out.astimezone(tz)
            if attendance.overtime_status == 'refused':
                check_out_tz -= timedelta(hours=attendance.validated_overtime_hours)
            if attendance.employee_id.resource_calendar_id and not attendance.employee_id.resource_calendar_id.flexible_hours:
                lunch_intervals = attendance.employee_id._employee_attendance_intervals(check_in_tz, check_out_tz, lunch=True)
                leaves = emp_cal._leave_intervals_batch(check_in_tz, check_out_tz, None)[False] if emp_cal else WorkIntervals([])
                real_lunch_intervals = lunch_intervals - leaves
                attendance_intervals = Intervals([(check_in_tz, check_out_tz, attendance)]) - real_lunch_intervals
            else:
                attendance_intervals = Intervals([(check_in_tz, check_out_tz, attendance)])
            for interval in attendance_intervals:
                intervals[attendance.employee_id.resource_id.id].append((
                    max(start_dt, interval[0]),
                    min(end_dt, interval[1]),
                    attendance))
        mapped_intervals = {r: WorkIntervals(intervals[r]) for r in resource_ids}
        mapped_intervals.update(super()._get_attendance_intervals(
            start_dt, end_dt))

        ##################################
        #   CALENDAR BASED CONTRACTS     #
        ##################################
        calendar_based_contracts = self.filtered(lambda c: c.work_entry_source == 'calendar')
        if not calendar_based_contracts:
            return mapped_intervals

        public_leaves = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),
            '|', ('calendar_id', '=', False), ('calendar_id', 'in', self.resource_calendar_id.ids),
            ('date_from', '<=', end_dt),
            ('date_to', '>=', start_dt)
        ])

        attendances = self.env['hr.attendance'].sudo().search([
            ('employee_id', 'in', calendar_based_contracts.employee_id.ids),
            ('check_in', '<=', end_dt),
            ('check_out', '>=', start_dt), #We ignore attendances without check_out date
            ('overtime_status', '=', 'approved'),
        ])

        resource_ids = attendances.employee_id.resource_id.ids
        work_intervals_by_resources = {
            resource_id: WorkIntervals(list(intervals)) for resource_id, intervals in mapped_intervals.items()
        }

        work_intervals_by_resource_day = defaultdict(lambda: defaultdict(list))
        for resource_id, intervals in mapped_intervals.items():
            if resource_id not in resource_ids:
                continue
            for interval in intervals:
                start = interval[0]
                day = (start.year, start.month, start.day)
                work_intervals_by_resource_day[resource_id][day].append(interval)

        lunch_intervals_by_resource = self._get_lunch_intervals(start_dt, end_dt)

        for attendance in attendances:
            resource = attendance.employee_id.resource_id
            work_intervals = work_intervals_by_resources[resource.id]
            tz = timezone(resource.tz)
            check_in_tz = attendance.check_in.astimezone(tz)
            check_out_tz = attendance.check_out.astimezone(tz)
            attendance_intervals = WorkIntervals([(check_in_tz, check_out_tz, attendance)])

            contract = attendance.employee_id._get_contracts(attendance.check_in, attendance.check_out, states=['open', 'close'])
            public_holiday = public_leaves.filtered(lambda pl:
                (not pl.calendar_id or pl.calendar_id == contract.resource_calendar_id) \
                and pl.date_from <= attendance.check_out \
                and pl.date_to >= attendance.check_in)
            if public_holiday:
                holiday_start = public_holiday[0].date_from.astimezone(tz)
                holiday_end = public_holiday[0].date_to.astimezone(tz)
                new_work_intervals = []
                for (start, end, calendar_attendance) in work_intervals:
                    if start > holiday_end or end < holiday_start or check_in_tz > end or check_out_tz < start:
                        new_work_intervals.append((start, end, calendar_attendance))
                    elif start > check_in_tz and end < check_out_tz:
                        continue
                    elif start < check_out_tz and end > check_in_tz:
                        if start < check_in_tz:
                            new_work_intervals.append((start, check_in_tz, calendar_attendance))
                        if end > check_out_tz:
                            new_work_intervals.append((check_out_tz, end, calendar_attendance))
                work_intervals = WorkIntervals(new_work_intervals)
            lunch_intervals = lunch_intervals_by_resource.get(resource.id, WorkIntervals([]))
            overtime_intervals = attendance_intervals - work_intervals - lunch_intervals
            if self.company_id.overtime_company_threshold:
                overtime_intervals = WorkIntervals([
                    (start, end, calendar_attendance) \
                    for (start, end, calendar_attendance) in overtime_intervals \
                    if (end - start).seconds / 60 > self.company_id.overtime_company_threshold])
            work_intervals_by_resources[resource.id] = work_intervals | overtime_intervals
        return work_intervals_by_resources

    def _get_interval_work_entry_type(self, interval):
        self.ensure_one()
        if self.work_entry_source == 'attendance': # The overtimes are only in the case of a contract based on the calendar
            return super()._get_interval_work_entry_type(interval)
        if 'overtime_work_entry_type_id' in interval[2] and interval[2].overtime_work_entry_type_id[:1]:
            return interval[2].overtime_work_entry_type_id[:1]
        if isinstance(interval[2], self.env['hr.attendance'].__class__):
            return self.env.ref('hr_work_entry.overtime_work_entry_type')
        return super()._get_interval_work_entry_type(interval)

    def _get_valid_leave_intervals(self, attendances, interval):
        self.ensure_one()
        badge_attendances = WorkIntervals([
            (start, end, record) for (start, end, record) in attendances \
            if start <= interval[1] and end > interval[0] and isinstance(record, self.env['hr.attendance'].__class__)])
        if badge_attendances:
            leave_interval = WorkIntervals([interval])
            return list(leave_interval - badge_attendances)
        return super()._get_valid_leave_intervals(attendances, interval)
