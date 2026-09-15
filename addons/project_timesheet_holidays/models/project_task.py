from odoo import fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ProjectTask(models.Model):
    _name = "project.task"
    _inherit = "project.task"

    leave_types_count = fields.Integer(
        string="Time Off Types Count",
        compute="_compute_leave_types_count",
    )
    is_timeoff_task = fields.Boolean(
        string="Is Time off Task",
        export_string_translation=False,
        compute="_compute_is_timeoff_task",
        search="_search_is_timeoff_task",
        groups="hr_timesheet.group_hr_timesheet_user",
    )

    def _compute_leave_types_count(self):
        timesheet_read_group = self.env["account.analytic.line"]._read_group(
            [
                ("task_id", "in", self.ids),
                "|",
                ("holiday_id", "!=", False),
                ("global_leave_id", "!=", False),
            ],
            ["task_id"],
            ["__count"],
        )
        timesheet_count_per_task = {
            timesheet_task.id: count for timesheet_task, count in timesheet_read_group
        }
        _debug.perf.count(
            "timeoff_task_leave_types",
            tasks=self,
            tasks_with_timeoff_timesheets=len(timesheet_count_per_task),
        )
        for task in self:
            task.leave_types_count = timesheet_count_per_task.get(task.id, 0)

    def _compute_is_timeoff_task(self):
        timeoff_tasks = self.filtered(
            lambda task: (
                task.leave_types_count
                or task.company_id.leave_timesheet_task_id == task
            )
        )
        _debug.logic(
            "timeoff_task_verdict",
            tasks=self,
            timeoff=timeoff_tasks,
            company_leave_task=self.env.company.leave_timesheet_task_id,
        )
        timeoff_tasks.is_timeoff_task = True
        (self - timeoff_tasks).is_timeoff_task = False

    def _search_is_timeoff_task(self, operator, value):
        if operator != "in":
            _debug.logic(
                "timeoff_task_search_unsupported", operator=operator, value=value
            )
            return NotImplemented

        timeoff_tasks_ids = {
            row[0]
            for row in self.env.execute_query(
                self.env["account.analytic.line"]
                ._search(
                    [
                        ("task_id", "!=", False),
                        "|",
                        ("holiday_id", "!=", False),
                        ("global_leave_id", "!=", False),
                    ],
                )
                .select("DISTINCT task_id")
            )
        }

        if self.env.company.leave_timesheet_task_id:
            timeoff_tasks_ids.add(self.env.company.leave_timesheet_task_id.id)

        _debug.pipeline(
            "timeoff_task_search_resolved",
            tasks=len(timeoff_tasks_ids),
            company=self.env.company,
        )
        return Domain("id", "in", tuple(timeoff_tasks_ids))
