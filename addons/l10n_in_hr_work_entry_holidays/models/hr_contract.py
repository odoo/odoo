
import pytz
from collections import defaultdict
from datetime import datetime, time, timedelta

from odoo import models
from odoo.addons.resource.models.utils import datetime_to_string


class HrContract(models.Model):
    _inherit = 'hr.contract'

    def _get_contract_work_entries_values(self, date_start, date_stop):
        def is_non_working_day(date):
            return not calendar._works_on_date(date)

        def get_working_day(date, step):
            current_date = date + timedelta(days=step)
            while is_non_working_day(current_date):
                current_date += timedelta(days=step)
            return current_date

        def ensure_timezone(dt, target_tz):
            if not dt.tzinfo:
                dt = pytz.utc.localize(dt)
            return dt.astimezone(target_tz)

        result = super()._get_contract_work_entries_values(date_start, date_stop)
        in_contracts = self.filtered(lambda c: c.company_id.country_id.code == 'IN')
        if not in_contracts:
            return result

        holiday_status_cache = {}
        start_dt = ensure_timezone(date_start, pytz.utc)
        end_dt = ensure_timezone(date_stop, pytz.utc)
        employees = in_contracts.mapped('employee_id')
        employee_ids = employees.ids
        existing_entries = {(vals['date_start'], vals['date_stop']) for vals in result}
        leaves = self.env['hr.leave'].search([
            ('employee_id', 'in', employee_ids),
            ('state', '=', 'validate'),
            ('date_from', '<=', datetime_to_string(end_dt)),
            ('date_to', '>=', datetime_to_string(start_dt)),
            ('l10n_in_contains_sandwich_leaves', '=', True),
        ])

        leaves_by_employee = defaultdict(list)
        for leave in leaves:
            leaves_by_employee[leave.employee_id.id].append(leave)


        for contract in in_contracts:
            employee = contract.employee_id
            calendar = contract.resource_calendar_id
            resource = employee.resource_id
            tz = pytz.timezone(calendar.tz)

            attendance_intervals = list(calendar._attendance_intervals_batch(start_dt, end_dt, resources=resource, tz=tz)[resource.id])
            working_start_time_utc = (
                attendance_intervals[0][0].astimezone(pytz.utc).time()
                if attendance_intervals else time(8, 0)
            )
            attendance_dates = {interval[0].date() for interval in attendance_intervals}

            employee_leaves = leaves_by_employee[employee.id]
            if not employee_leaves:
                continue

            for leave in employee_leaves:
                entries_to_update = []
                new_work_entries = []
                holiday_status_id = leave.holiday_status_id.id
                if holiday_status_id not in holiday_status_cache:
                    holiday_status_cache[holiday_status_id] = leave.holiday_status_id.work_entry_type_id
                leave_work_entry_type = holiday_status_cache[holiday_status_id]

                leave_start_dt = max(start_dt, ensure_timezone(leave.date_from, tz))
                leave_end_dt = min(end_dt, ensure_timezone(leave.date_to, tz))

                if leave.linked_sandwich_leave_id:
                    linked_leave = leave.linked_sandwich_leave_id
                    leave_start_dt = min(leave_start_dt, ensure_timezone(linked_leave.date_to, tz))
                    leave_end_dt = max(leave_end_dt, ensure_timezone(linked_leave.date_from, tz))
                    if not linked_leave.has_edge_public_leave:
                        leave_start_dt += timedelta(days=1)
                        leave_end_dt += timedelta(days=-1)
                elif is_non_working_day(leave_start_dt) and is_non_working_day(leave_end_dt):
                    leave_start_dt = get_working_day(leave_start_dt, 1)
                    leave_end_dt = get_working_day(leave_end_dt, -1)

                leave_start_dt = leave_start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
                leave_end_dt = leave_end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)

                public_holidays = self.env['resource.calendar.leaves'].search([
                    ('resource_id', '=', False),
                    ('company_id', '=', leave.company_id.id),
                    ('calendar_id', 'in', [False, calendar.id]),
                    ('date_from', '>=', datetime_to_string(leave_start_dt)),
                    ('date_to', '<=', datetime_to_string(leave_end_dt)),
                ])

                if public_holidays:
                    holiday_work_entry_type_ids = public_holidays.mapped('work_entry_type_id').ids
                    if holiday_work_entry_type_ids:
                        public_holidays_work_entries = self.env['hr.work.entry'].search([
                            ('date_start', '>=', datetime_to_string(leave_start_dt)),
                            ('date_stop', '<=', datetime_to_string(leave_end_dt)),
                            ('employee_id', '=', employee.id),
                            ('work_entry_type_id', 'in', holiday_work_entry_type_ids),
                        ])
                        if public_holidays_work_entries:
                            entry_name = f"{leave_work_entry_type.name + ': ' if leave_work_entry_type else ''}{employee.name}"
                            public_holidays_work_entries.write({
                                'work_entry_type_id': leave_work_entry_type.id,
                                'leave_id': leave.id,
                                'name': entry_name
                            })

                for entry in result:
                    if not entry.get('leave_id'):
                        entry_date = entry['date_start'].date()
                        if leave.linked_sandwich_leave_id:
                            if leave_start_dt.date() <= entry_date <= leave_end_dt.date():
                                entries_to_update.append(entry)
                        else:
                            if leave_start_dt.date() < entry_date < leave_end_dt.date():
                                entries_to_update.append(entry)

                if entries_to_update:
                    entry_name = f"{leave_work_entry_type.name + ': ' if leave_work_entry_type else ''}{employee.name}"
                    update_values = {
                        'work_entry_type_id': leave_work_entry_type.id,
                        'leave_id': leave.id,
                        'name': entry_name
                    }
                    for entry in entries_to_update:
                        entry.update(update_values)

                leave_dates = {
                    leave_start_dt.date() + timedelta(days=i)
                    for i in range((leave_end_dt.date() - leave_start_dt.date()).days + 1)
                }
                public_holiday_dates = {
                    h.date_from.date()
                    for h in public_holidays
                } if leave.linked_sandwich_leave_id else set()
                missing_dates = sorted(leave_dates - attendance_dates - public_holiday_dates)

                for missing_date in missing_dates:
                    work_entry_start = datetime.combine(missing_date, working_start_time_utc)
                    work_entry_stop = work_entry_start + timedelta(hours=calendar.hours_per_day)
                    if (work_entry_start, work_entry_stop) not in existing_entries:
                        new_work_entries.append({
                            'name': f"{leave_work_entry_type.name + ': ' if leave_work_entry_type else ''}{employee.name}",
                            'date_start': work_entry_start,
                            'date_stop': work_entry_stop,
                            'work_entry_type_id': leave_work_entry_type.id,
                            'employee_id': employee.id,
                            'company_id': contract.company_id.id,
                            'state': 'draft',
                            'contract_id': contract.id,
                            'leave_id': leave.id,
                        })
                result.extend(new_work_entries)
        return result
