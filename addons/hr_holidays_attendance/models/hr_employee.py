# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import UTC
from zoneinfo import ZoneInfo

from odoo import fields, models
from odoo.fields import Domain


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    attendance_based = fields.Boolean(readonly=False, related="version_id.attendance_based", inherited=True, groups="hr.group_hr_user")

    def _get_calendar_attendance_domain(self):
        return Domain.AND([
            super()._get_calendar_attendance_domain(),
            Domain.OR([
                Domain("work_entry_type_id", "=", False),
                Domain("work_entry_type_id.count_as", "!=", "absence")
            ]),
        ])

    def _compute_total_overtime(self):
        overtime_by_employee = dict(self.env['hr.attendance']._read_group(
            domain=[
                ('employee_id', 'in', self.ids),
                ('is_time_rule_output', '=', True),
            ],
            groupby=['employee_id'],
            aggregates=['worked_hours:sum'],
        ))
        for employee in self:
            employee.total_overtime = overtime_by_employee.get(employee, 0.0)

    def _compute_hours_last_month(self):
        super()._compute_hours_last_month()
        now = fields.Datetime.now()
        now_utc = now.replace(tzinfo=UTC)
        for timezone, employees in self.grouped('tz').items():
            tz = ZoneInfo(timezone or 'UTC')
            now_tz = now_utc.astimezone(tz)
            start_tz = now_tz.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            start_naive = start_tz.astimezone(UTC).replace(tzinfo=None)
            end_naive = now_tz.astimezone(UTC).replace(tzinfo=None)

            overtime_by_employee = dict(self.env['hr.attendance']._read_group(
                domain=[
                    ('is_time_rule_output', '=', True),
                    ('employee_id', 'in', employees.ids),
                    ('check_in', '<', end_naive),
                    ('check_out', '>', start_naive),
                ],
                groupby=['employee_id'],
                aggregates=['worked_hours:sum'],
            ))
            for employee in employees:
                employee.hours_last_month_overtime = round(
                    overtime_by_employee.get(employee, 0.0), 2
                )

    def get_attendace_data_by_employee(self, date_start, date_stop):
        attendance_data = super().get_attendace_data_by_employee(date_start, date_stop)

        overtime_atts = self.env['hr.attendance']._read_group(
            domain=[
                ('is_time_rule_output', '=', True),
                ('employee_id', 'in', self.ids),
                ('check_in', '<', date_stop),
                ('check_out', '>', date_start),
            ],
            groupby=['employee_id'],
            aggregates=['worked_hours:sum'],
        )
        for employee, overtime_hours in overtime_atts:
            attendance_data[employee.id]['overtime_hours'] = overtime_hours

        return attendance_data
