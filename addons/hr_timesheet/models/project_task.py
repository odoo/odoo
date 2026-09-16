import re
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

from odoo.addons.rating.models.rating_data import OPERATOR_MAPPING

PROJECT_TASK_READABLE_FIELDS = {
    "allocated_hours",
    "allow_timesheets",
    "analytic_account_active",
    "effective_hours",
    "encode_uom_in_days",
    "planned_hours",
    "progress",
    "overtime",
    "remaining_hours",
    "subtask_effective_hours",
    "subtask_planned_hours",
    "timesheet_ids",
    "total_hours_spent",
}

_debug = DebugLog(__name__)


class ProjectTask(models.Model):
    _name = "project.task"
    _inherit = "project.task"

    project_id = fields.Many2one(
        domain="['|', ('company_id', '=', False), ('company_id', '=?',  company_id), ('is_internal_project', '=', False), ('is_template', 'in', [is_template, False])]"
    )
    analytic_account_active = fields.Boolean(
        related="project_id.analytic_account_active",
        string="Active Analytic Account",
        export_string_translation=False,
    )
    allow_timesheets = fields.Boolean(
        string="Allow timesheets",
        export_string_translation=False,
        compute="_compute_allow_timesheets",
        search="_search_allow_timesheets",
        compute_sudo=True,
        readonly=True,
    )
    remaining_hours = fields.Float(
        string="Time Remaining",
        compute="_compute_remaining_hours",
        store=True,
        readonly=True,
        help="Number of planned hours minus the number of hours spent.",
    )
    remaining_hours_percentage = fields.Float(
        export_string_translation=False,
        compute="_compute_remaining_hours_percentage",
        search="_search_remaining_hours_percentage",
    )
    effective_hours = fields.Float(
        string="Time Spent",
        compute="_compute_effective_hours",
        compute_sudo=True,
        store=True,
    )
    total_hours_spent = fields.Float(
        string="Total Time Spent",
        compute="_compute_total_hours_spent",
        store=True,
        help="Time spent on this task and its sub-tasks (and their own sub-tasks).",
    )
    progress = fields.Float(
        compute="_compute_progress_hours",
        store=True,
        aggregator="avg",
    )
    overtime = fields.Float(
        compute="_compute_progress_hours",
        store=True,
    )
    subtask_effective_hours = fields.Float(
        string="Time Spent on Sub-tasks",
        compute="_compute_subtask_effective_hours",
        recursive=True,
        store=True,
        help="Time spent on the sub-tasks (and their own sub-tasks) of this task.",
    )
    timesheet_ids = fields.One2many(
        comodel_name="account.analytic.line",
        inverse_name="task_id",
        string="Timesheets",
        export_string_translation=False,
    )
    encode_uom_in_days = fields.Boolean(
        export_string_translation=False,
        compute="_compute_encode_uom_in_days",
        default=lambda self: self._uom_in_days(),
    )
    display_name = fields.Char(
        help="""Use these keywords in the title to set new tasks:\n
        30h Plan 30 hours for the task
        #tags Set tags on the task
        @user Assign the task to a user
        ! Set the task a medium priority
        !! Set the task a high priority
        !!! Set the task a urgent priority\n
        Make sure to use the right format and order e.g. Improve the configuration screen 5h #feature #v16 @Mitchell !"""
    )

    @property
    def TASK_PORTAL_READABLE_FIELDS(self):
        return super().TASK_PORTAL_READABLE_FIELDS | PROJECT_TASK_READABLE_FIELDS

    @api.constrains("project_id")
    def _check_project_root(self):
        private_tasks = self.filtered(lambda t: not t.project_id)
        if private_tasks and self.env["account.analytic.line"].sudo().search_count(
            [("task_id", "in", private_tasks.ids)], limit=1
        ):
            _debug.logic(
                "private_task_refused", reason="has_timesheets", tasks=private_tasks
            )
            raise UserError(
                _(
                    "This task cannot be private because there are some timesheets linked to it."
                )
            )

    def _uom_in_days(self):
        return self.env.company.timesheet_encode_uom_id == self.env.ref(
            "uom.product_uom_day"
        )

    def _compute_encode_uom_in_days(self):
        self.encode_uom_in_days = self._uom_in_days()

    @api.depends("project_id.allow_timesheets")
    def _compute_allow_timesheets(self):
        for task in self:
            task.allow_timesheets = task.project_id.allow_timesheets

    def _search_allow_timesheets(self, operator, value):
        query = (
            self.env["project.project"]
            .sudo()
            ._search(
                [
                    ("allow_timesheets", operator, value),
                ]
            )
        )
        return [("project_id", "in", query)]

    @api.depends("timesheet_ids.unit_amount")
    def _compute_effective_hours(self):
        if not any(self._ids):
            _debug.logic("effective_hours", by="in_memory", tasks=self)
            for task in self:
                task.effective_hours = sum(task.timesheet_ids.mapped("unit_amount"))
            return
        _debug.perf.count("effective_hours_grouped", tasks=self)
        timesheet_read_group = self.env["account.analytic.line"]._read_group(
            [("task_id", "in", self.ids)], ["task_id"], ["unit_amount:sum"]
        )
        timesheets_per_task = {task.id: amount for task, amount in timesheet_read_group}
        for task in self:
            task.effective_hours = timesheets_per_task.get(task.id, 0.0)

    @api.depends("effective_hours", "subtask_effective_hours", "planned_hours")
    def _compute_progress_hours(self):
        for task in self:
            if task.planned_hours > 0.0:
                task_total_hours = task.effective_hours + task.subtask_effective_hours
                task.overtime = max(task_total_hours - task.planned_hours, 0)
                task.progress = round(task_total_hours / task.planned_hours, 2)
            else:
                task.progress = 0.0
                task.overtime = 0

    @api.depends("planned_hours", "remaining_hours")
    def _compute_remaining_hours_percentage(self):
        for task in self:
            if task.planned_hours > 0.0:
                task.remaining_hours_percentage = (
                    task.remaining_hours / task.planned_hours
                )
            else:
                task.remaining_hours_percentage = 0.0

    def _search_remaining_hours_percentage(self, operator, value):
        if operator not in OPERATOR_MAPPING:
            return NotImplemented
        if operator in ("in", "not in"):
            value = tuple(value)
        sql = SQL(
            """(
            SELECT id
              FROM %s
             WHERE remaining_hours > 0
               AND planned_hours > 0
               AND remaining_hours / planned_hours %s %s
        )""",
            SQL.identifier(self._table),
            SQL(operator),  # noqa: E8501  caller whitelists the operator
            value,
        )
        return [("id", "in", sql)]

    @api.depends("effective_hours", "subtask_effective_hours", "planned_hours")
    def _compute_remaining_hours(self):
        for task in self:
            if not task.planned_hours:
                task.remaining_hours = 0.0
            else:
                task.remaining_hours = (
                    task.planned_hours
                    - task.effective_hours
                    - task.subtask_effective_hours
                )

    @api.depends("effective_hours", "subtask_effective_hours")
    def _compute_total_hours_spent(self):
        for task in self:
            task.total_hours_spent = task.effective_hours + task.subtask_effective_hours

    @api.depends("child_ids.effective_hours", "child_ids.subtask_effective_hours")
    def _compute_subtask_effective_hours(self):
        for task in self.with_context(active_test=False):
            task.subtask_effective_hours = sum(
                child_task.effective_hours + child_task.subtask_effective_hours
                for child_task in task.child_ids
            )

    def _get_pattern_per_group(self):
        return {
            **super()._get_pattern_per_group(),
            "planned_hours": r"\s(\d+(?:\.\d+)?)[hH]",
        }

    def _get_patterns_in_group_order(self):
        return [
            self._get_pattern_per_group()["planned_hours"]
        ] + super()._get_patterns_in_group_order()

    def _get_cannot_start_with_patterns(self):
        return super()._get_cannot_start_with_patterns() + [r"(?!\d+(?:\.\d+)?(?:h|H))"]

    def _extract_planned_hours(self, title):
        planned_hours_group = self._get_pattern_per_group()["planned_hours"]
        if not self.allow_timesheets:
            return title
        self.planned_hours = sum(
            float(num) for num in re.findall(planned_hours_group, title)
        )
        self.env.remove_to_compute(self._fields["planned_hours"], self)
        return re.subn(planned_hours_group, "", title)[0]

    def _get_extractors_in_group_order(self):
        return [
            lambda task, title: task._extract_planned_hours(title)
        ] + super()._get_extractors_in_group_order()

    def action_view_subtask_timesheet(self):
        self.check_singleton()
        is_internal_user = self.env.user.has_group("base.group_user")
        task_ids = (
            self.with_context(active_test=False)
            ._get_subtask_ids_per_task_id()
            .get(self.id, [])
        )
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "hr_timesheet.timesheet_action_all"
        )
        graph_view_id = self.env.ref(
            "hr_timesheet.view_hr_timesheet_line_graph_by_employee"
        ).id
        new_views = []
        for view in action["views"]:
            if (
                not is_internal_user or self.env.context.get("is_project_sharing")
            ) and view[1] not in ["tree", "kanban", "form"]:
                continue
            if not is_internal_user:
                if view[1] == "list":
                    tree_view_id = self.env["ir.model.data"]._xmlid_to_res_id(
                        "hr_timesheet.hr_timesheet_line_portal_tree"
                    )
                    if tree_view_id:
                        new_views.insert(0, (tree_view_id, "list"))
                        continue
                elif view[1] == "form":
                    form_view_id = self.env["ir.model.data"]._xmlid_to_res_id(
                        "hr_timesheet.timesheet_view_form_portal_user"
                    )
                    if form_view_id:
                        new_views.append((form_view_id, "form"))
                        continue
                elif view[1] == "kanban":
                    kanban_view_id = self.env["ir.model.data"]._xmlid_to_res_id(
                        "hr_timesheet.view_kanban_account_analytic_line_portal_user"
                    )
                    if kanban_view_id:
                        new_views.append((kanban_view_id, "kanban"))
                        continue
            if view[1] == "graph":
                view = (graph_view_id, "graph")
            new_views.insert(0, view) if view[1] == "list" else new_views.append(view)

        action.update(
            {
                "display_name": _("Timesheets"),
                "context": {"default_project_id": self.project_id.id},
                "domain": [("project_id", "!=", False), ("task_id", "in", task_ids)],
                "views": new_views,
            }
        )
        return action

    def _get_timesheet(self):
        return self.timesheet_ids

    def _get_timesheet_report_data(self):
        subtasks = self._get_all_subtasks()
        timesheets_read_group = self.env["account.analytic.line"]._read_group(
            [("task_id", "in", (self | subtasks).ids)],
            ["task_id"],
            ["id:recordset"],
        )
        timesheets_per_task = dict(timesheets_read_group)
        subtask_ids_per_task_id = defaultdict(list)
        for subtask in subtasks:
            subtask_ids_per_task_id[subtask.parent_id.id].append(subtask.id)
        return {
            "subtask_ids_per_task_id": subtask_ids_per_task_id,
            "timesheets_per_task": timesheets_per_task,
        }

    @api.depends_context("hr_timesheet_display_remaining_hours")
    def _compute_display_name(self):
        super()._compute_display_name()
        if self.env.context.get("hr_timesheet_display_remaining_hours"):
            for task in self:
                if (
                    task.allow_timesheets
                    and task.allocated_hours > 0
                    and task.encode_uom_in_days
                ):
                    days_left = _(
                        "(%s days remaining)",
                        task._convert_hours_to_days(task.remaining_hours),
                    )
                    task.display_name = task.display_name + "\u00a0" + days_left
                elif task.allow_timesheets and task.allocated_hours > 0:
                    hours, mins = (
                        str(int(duration)).rjust(2, "0")
                        for duration in divmod(abs(task.remaining_hours) * 60, 60)
                    )
                    hours_left = _(
                        "(%(sign)s%(hours)s:%(minutes)s remaining)",
                        sign="-" if task.remaining_hours < 0 else "",
                        hours=hours,
                        minutes=mins,
                    )
                    task.display_name = task.display_name + "\u00a0" + hours_left

    @api.ondelete(at_uninstall=False)
    def _unlink_except_contains_entries(self):
        timesheet_data = (
            self.env["account.analytic.line"]
            .sudo()
            ._read_group(
                [("task_id", "in", self.ids)],
                ["task_id"],
            )
        )
        task_with_timesheets_ids = [task.id for (task,) in timesheet_data]
        if not task_with_timesheets_ids:
            return
        inaccessible_task_ids = set(task_with_timesheets_ids) - set(
            self.env["account.analytic.line"]
            .search([("task_id", "in", task_with_timesheets_ids)])
            .mapped("task_id.id")
        )
        if inaccessible_task_ids:
            _debug.logic(
                "task_unlink_refused",
                reason="inaccessible_timesheets",
                tasks=len(inaccessible_task_ids),
            )
            raise UserError(
                _(
                    "This task can’t be deleted because it’s linked to timesheets. Please contact someone with higher access to remove the timesheets first, "
                    "and then you’ll be able to delete the task."
                )
            )
        if len(task_with_timesheets_ids) > 1:
            warning_msg = _(
                "Some timesheet entries are weighing down these tasks! Remove them first, then you’ll be able to delete the tasks!"
            )
        else:
            warning_msg = _(
                "Some timesheet entries are weighing down these tasks! Remove them first, then you’ll be able to delete the tasks!"
            )
        _debug.logic(
            "task_unlink_refused",
            reason="has_timesheets",
            tasks=len(task_with_timesheets_ids),
        )
        raise RedirectWarning(
            warning_msg,
            self.env.ref("hr_timesheet.timesheet_action_task").id,
            _("See timesheet entries"),
            {"active_ids": task_with_timesheets_ids},
        )

    @api.model
    def _convert_hours_to_days(self, time):
        uom_hour = self.env.ref("uom.product_uom_hour")
        uom_day = self.env.ref("uom.product_uom_day")
        return round(
            uom_hour._get_quantity_in_unit(time, uom_day, raise_if_failure=False), 2
        )

    def _get_portal_total_hours_dict(self):
        if not (timesheetable_tasks := self.filtered("allow_timesheets")):
            return {}
        return {
            "allocated_hours": sum(timesheetable_tasks.mapped("allocated_hours")),
            "effective_hours": sum(timesheetable_tasks.mapped("effective_hours")),
        }
