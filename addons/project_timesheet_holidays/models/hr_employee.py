from collections import defaultdict

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.model_create_multi
    def create(self, vals_list):
        employees = super().create(vals_list)
        if self.env.context.get("salary_simulation"):
            _debug.logic(
                "public_holiday_timesheets_skipped",
                reason="salary_simulation",
                employees=employees,
            )
            return employees

        self.with_context(
            allowed_company_ids=employees.company_id.ids
        )._create_future_public_holidays_timesheets(employees)
        return employees

    def write(self, vals):
        if vals.get("active"):
            inactive_emp = self.filtered(lambda e: not e.active)
        result = super().write(vals)
        self_company = self.with_context(allowed_company_ids=self.company_id.ids)
        if "active" in vals:
            if vals.get("active"):
                inactive_emp = inactive_emp.with_env(self_company.env)
                _debug.lifecycle(
                    "public_holiday_timesheets_regenerated",
                    trigger="employee_reactivated",
                    employees=inactive_emp,
                )
                inactive_emp._create_future_public_holidays_timesheets(inactive_emp)
            else:
                _debug.lifecycle(
                    "public_holiday_timesheets_dropped",
                    trigger="employee_archived",
                    employees=self,
                )
                self_company._remove_future_public_holidays_timesheets()
        elif "resource_calendar_id" in vals:
            _debug.lifecycle(
                "public_holiday_timesheets_regenerated",
                trigger="calendar_changed",
                employees=self,
                calendar_id=vals["resource_calendar_id"],
            )
            self_company._remove_future_public_holidays_timesheets()
            self_company._create_future_public_holidays_timesheets(self_company)
        return result

    def _remove_future_public_holidays_timesheets(self):
        future_timesheets = (
            self.env["account.analytic.line"]
            .sudo()
            .search(
                [
                    ("global_leave_id", "!=", False),
                    ("date", ">=", fields.Date.today()),
                    ("employee_id", "in", self.ids),
                ]
            )
        )
        _debug.pipeline(
            "future_public_holiday_timesheets_removed",
            employees=self,
            timesheets=future_timesheets,
        )
        future_timesheets.write({"global_leave_id": False})
        future_timesheets.unlink()

    def _create_future_public_holidays_timesheets(self, employees):
        lines_vals = []
        today = fields.Datetime.today()
        global_leaves_wo_calendar = defaultdict(
            lambda: self.env["resource.schedule.exception"]
        )
        global_leaves_wo_calendar.update(
            dict(
                self.env["resource.schedule.exception"]._read_group(
                    [
                        ("calendar_id", "=", False),
                        ("resource_id", "=", False),
                        ("date_from", ">=", today),
                    ],
                    groupby=["company_id"],
                    aggregates=["id:recordset"],
                )
            )
        )
        _debug.pipeline(
            "public_holiday_timesheets_start",
            employees=employees,
            companies_with_calendarless_leaves=len(global_leaves_wo_calendar),
        )
        for employee in employees:
            if not employee.active:
                _debug.logic(
                    "public_holiday_timesheets_skipped",
                    reason="inactive_employee",
                    employee=employee,
                )
                continue
            global_leaves = (
                employee.resource_calendar_id.global_leave_ids.filtered(
                    lambda l: l.date_from >= today
                )
                + global_leaves_wo_calendar[employee.company_id]
            )
            work_hours_data = global_leaves._work_time_per_day()
            _debug.perf.count(
                "public_holiday_work_time_per_day",
                employee=employee,
                global_leaves=global_leaves,
                calendars=len(work_hours_data),
            )
            for global_time_off in global_leaves:
                # `_work_time_per_day` keys by calendar first and by leave
                # second; both reads below take the pair.
                leave_days = work_hours_data[employee.resource_calendar_id.id][
                    global_time_off.id
                ]
                _debug.logic(
                    "public_holiday_line_total",
                    employee=employee,
                    global_time_off=global_time_off,
                    days=len(leave_days),
                )
                for index, (day_date, work_hours_count) in enumerate(leave_days):
                    lines_vals.append(
                        global_time_off._timesheet_prepare_line_values(
                            index,
                            employee,
                            leave_days,
                            day_date,
                            work_hours_count,
                        )
                    )
        _debug.pipeline(
            "public_holiday_timesheets_created",
            employees=employees,
            lines=len(lines_vals),
        )
        return self.env["account.analytic.line"].sudo().create(lines_vals)
