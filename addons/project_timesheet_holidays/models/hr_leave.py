from odoo import _, fields, models
from odoo.fields import Domain
from odoo.libs.datetime import timezone
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrLeave(models.Model):
    _inherit = "hr.leave"

    timesheet_ids = fields.One2many(
        comodel_name="account.analytic.line",
        inverse_name="holiday_id",
        string="Analytic Lines",
    )

    def _apply_leave_request(self):
        self._create_timesheets()
        return super()._apply_leave_request()

    def _create_timesheets(self, ignored_schedule_exceptions=None):
        vals_list = []
        leave_ids = []
        calendar_leaves_data = self.env["resource.schedule.exception"]._read_group(
            [("holiday_id", "in", self.ids)], ["holiday_id"], ["id:array_agg"]
        )
        mapped_calendar_leaves = {
            leave: calendar_leave_ids[0]
            for leave, calendar_leave_ids in calendar_leaves_data
        }
        for leave in self:
            project, task = (
                leave.employee_id.company_id.internal_project_id,
                leave.employee_id.company_id.leave_timesheet_task_id,
            )

            if not project or not task or leave.holiday_status_id.time_type_id.is_work:
                _debug.logic(
                    "leave_timesheets_skipped",
                    reason="no_internal_project"
                    if not project
                    else "no_leave_task"
                    if not task
                    else "time_type_other",
                    leave=leave,
                    company=leave.employee_id.company_id,
                )
                continue

            leave_ids.append(leave.id)
            if not leave.employee_id:
                _debug.logic(
                    "leave_timesheets_skipped", reason="no_employee", leave=leave
                )
                continue

            calendar = leave.employee_id.resource_calendar_id
            calendar_timezone = timezone((calendar or leave.employee_id).tz)

            if calendar.flexible_hours and (
                leave.request_unit_hours
                or leave.request_unit_half
                or leave.date_from.date() == leave.date_to.date()
            ):
                leave_date = leave.date_from.astimezone(calendar_timezone).date()
                if leave.request_unit_hours:
                    hours = leave.request_hour_to - leave.request_hour_from
                elif leave.request_unit_half:
                    hours = calendar.hours_per_day / 2
                else:
                    hours = calendar.hours_per_day
                work_hours_data = [(leave_date, hours)]
                _debug.logic(
                    "leave_timesheets_flexible_day",
                    leave=leave,
                    unit="hours"
                    if leave.request_unit_hours
                    else "half"
                    if leave.request_unit_half
                    else "day",
                    hours=hours,
                    date=leave_date,
                )
            else:
                ignored_schedule_exceptions = ignored_schedule_exceptions or []
                if leave in mapped_calendar_leaves:
                    ignored_schedule_exceptions.append(mapped_calendar_leaves[leave])
                work_hours_data = leave.employee_id._list_work_time_per_day(
                    leave.date_from,
                    leave.date_to,
                    domain=[("id", "not in", ignored_schedule_exceptions)]
                    if ignored_schedule_exceptions
                    else None,
                )[leave.employee_id.id]
                _debug.perf.count(
                    "leave_timesheets_work_time_per_day",
                    leave=leave,
                    employee=leave.employee_id,
                    days=len(work_hours_data),
                    ignored_calendar_leaves=len(ignored_schedule_exceptions),
                )

            for index, (day_date, work_hours_count) in enumerate(work_hours_data):
                vals_list.append(
                    leave._timesheet_prepare_line_values(
                        index,
                        work_hours_data,
                        day_date,
                        work_hours_count,
                        project,
                        task,
                    )
                )

        old_timesheets = (
            self.env["account.analytic.line"]
            .sudo()
            .search([("project_id", "!=", False), ("holiday_id", "in", leave_ids)])
        )
        if old_timesheets:
            _debug.pipeline(
                "leave_timesheets_replaced",
                leaves=self,
                removed=old_timesheets,
            )
            old_timesheets.holiday_id = False
            old_timesheets.unlink()

        _debug.pipeline(
            "leave_timesheets_created",
            leaves=self,
            eligible_leaves=len(leave_ids),
            lines=len(vals_list),
        )
        self.env["account.analytic.line"].sudo().create(vals_list)

    def _timesheet_prepare_line_values(
        self, index, work_hours_data, day_date, work_hours_count, project, task
    ):
        self.check_singleton()
        return {
            "name": _(
                "Time Off (%(index)s/%(total)s)",
                index=index + 1,
                total=len(work_hours_data),
            ),
            "project_id": project.id,
            "task_id": task.id,
            "account_id": project.sudo().account_id.id,
            "unit_amount": work_hours_count,
            "user_id": self.employee_id.user_id.id,
            "date": day_date,
            "holiday_id": self.id,
            "employee_id": self.employee_id.id,
            "company_id": task.sudo().company_id.id or project.sudo().company_id.id,
        }

    def _check_missing_global_leave_timesheets(self):
        if not self:
            _debug.logic("global_leave_backfill_skipped", reason="empty_recordset")
            return
        min_date = min(self.mapped("date_from"))
        max_date = max(self.mapped("date_to"))

        leaves = self.env["resource.schedule.exception"]
        global_leaves = leaves.search(
            leaves._get_domain_public_holidays(min_date, max_date)
            & Domain("company_id.internal_project_id", "!=", False)
            & Domain("company_id.leave_timesheet_task_id", "!=", False)
        )
        _debug.pipeline(
            "global_leave_backfill",
            leaves=self,
            employees=self.employee_id,
            window_from=min_date,
            window_to=max_date,
            global_leaves=global_leaves,
        )
        if global_leaves:
            global_leaves._generate_public_time_off_timesheets(self.employee_id)

    def action_refuse(self):
        result = super().action_refuse()
        timesheets = self.sudo().mapped("timesheet_ids")
        _debug.lifecycle(
            "leave_timesheets_dropped",
            trigger="refused",
            leaves=self,
            timesheets=timesheets,
        )
        timesheets.write({"holiday_id": False})
        timesheets.unlink()
        self._check_missing_global_leave_timesheets()
        return result

    def _action_user_cancel(self, reason=None):
        res = super()._action_user_cancel(reason)
        timesheets = self.sudo().timesheet_ids
        _debug.lifecycle(
            "leave_timesheets_dropped",
            trigger="user_cancelled",
            leaves=self,
            timesheets=timesheets,
        )
        timesheets.write({"holiday_id": False})
        timesheets.unlink()
        self._check_missing_global_leave_timesheets()
        return res

    def _force_cancel(self, *args, **kwargs):
        super()._force_cancel(*args, **kwargs)
        timesheets = self.sudo().timesheet_ids
        _debug.lifecycle(
            "leave_timesheets_dropped",
            trigger="force_cancelled",
            leaves=self,
            timesheets=timesheets,
        )
        timesheets.holiday_id = False
        timesheets.unlink()

    def write(self, vals):
        res = super().write(vals)
        timesheet_ids_to_remove = []
        for leave in self:
            if leave.number_of_days == 0 and leave.sudo().timesheet_ids:
                _debug.lifecycle(
                    "leave_timesheets_dropped",
                    trigger="zero_days_after_write",
                    leaves=leave,
                    timesheets=leave.sudo().timesheet_ids,
                )
                leave.sudo().timesheet_ids.holiday_id = False
                timesheet_ids_to_remove.extend(leave.timesheet_ids)
        self.env["account.analytic.line"].browse(
            set(timesheet_ids_to_remove)
        ).sudo().unlink()
        return res
