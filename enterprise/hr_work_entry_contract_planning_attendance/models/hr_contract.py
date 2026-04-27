# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from pytz import timezone

from odoo import models
from odoo.addons.hr_work_entry_contract.models.hr_work_intervals import WorkIntervals


class HrContract(models.Model):
    _inherit = 'hr.contract'

    def _get_attendance_intervals(self, start_dt, end_dt):
        ##################################
        #   PLANNING BASED CONTRACTS     #
        ##################################
        mapped_intervals = super()._get_attendance_intervals(start_dt, end_dt)

        planning_based_contracts = self.filtered(lambda c: c.work_entry_source == 'planning')
        if not planning_based_contracts:
            return mapped_intervals

        attendances = self.env['hr.attendance'].sudo().search([
            ('employee_id', 'in', planning_based_contracts.employee_id.ids),
            ('check_in', '<=', end_dt),
            ('check_out', '>=', start_dt), #We ignore attendances without check_out date
        ])
        if not attendances:
            return mapped_intervals

        public_leaves = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),
            '|', ('calendar_id', '=', False), ('calendar_id', 'in', self.resource_calendar_id.ids),
            ('date_from', '<=', end_dt),
            ('date_to', '>=', start_dt),
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
            overtime_intervals = attendance_intervals - work_intervals
            if self.company_id.overtime_company_threshold:
                overtime_intervals = WorkIntervals([
                    (start, end, calendar_attendance) \
                    for (start, end, calendar_attendance) in overtime_intervals \
                    if (end - start).seconds / 60 > self.company_id.overtime_company_threshold])
            work_intervals_by_resources[resource.id] = work_intervals | overtime_intervals
        return work_intervals_by_resources
