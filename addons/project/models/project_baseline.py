from odoo import fields, models
from odoo.exceptions import UserError

from ..tools import debug_log as dbg


class ProjectBaseline(models.Model):
    _name = "project.baseline"
    _description = "Project Baseline"
    _order = "date_created desc, id desc"

    name = fields.Char(
        string="Baseline Name",
        required=True,
        help="e.g. 'Original Plan', 'Replan v2'.",
    )
    project_id = fields.Many2one(
        comodel_name="project.project",
        index=True,
        required=True,
        ondelete="cascade",
    )
    date_created = fields.Datetime(
        string="Created On",
        default=fields.Datetime.now,
        readonly=True,
    )
    created_by_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.user,
        readonly=True,
    )
    is_current = fields.Boolean(
        string="Current Baseline",
        default=False,
        copy=False,
        help="Only one baseline per project can be marked as current.",
    )
    line_ids = fields.One2many(
        comodel_name="project.baseline.line",
        inverse_name="baseline_id",
        string="Baseline Lines",
    )
    line_count = fields.Count(
        count_of="line_ids",
        string="Tasks Snapshot",
        export_string_translation=False,
    )

    _unique_current_baseline = models.UniqueIndex(
        "(project_id) WHERE (is_current IS TRUE)",
        "Only one baseline per project can be marked as current.",
    )

    def action_set_current(self) -> None:
        self.check_singleton()
        previous = self.project_id.baseline_ids.filtered("is_current")
        dbg.lifecycle.debug(
            "project.baseline.action_set_current %s [project:%s]: replacing %s",
            dbg.rec(self),
            self.project_id.id,
            dbg.rec(previous),
        )
        previous.write({"is_current": False})
        self.is_current = True

    @dbg.timed
    def action_capture_snapshot(self) -> None:
        self.check_singleton()
        if self.line_ids:
            raise UserError(
                self.env._(
                    "This baseline already has snapshot data. "
                    "Create a new baseline instead."
                )
            )
        tasks = self.env["project.task"].search(
            [
                ("project_id", "=", self.project_id.id),
                ("is_template", "=", False),
            ]
        )
        dbg.lifecycle.debug(
            "project.baseline.action_capture_snapshot %s [project:%s]: %d tasks",
            dbg.rec(self),
            self.project_id.id,
            len(tasks),
        )
        lines = [
            {
                "baseline_id": self.id,
                "task_id": task.id,
                "task_name": task.name,
                "date_planned_start": task.date_start,
                "date_planned_end": task.date_end,
                "planned_hours": task.planned_hours,
                "milestone_id": task.milestone_id.id,
                "step_id": task.step_id.id,
            }
            for task in tasks
        ]
        self.env["project.baseline.line"].create(lines)


class ProjectBaselineLine(models.Model):
    _name = "project.baseline.line"
    _description = "Baseline Task Snapshot"
    _order = "sequence, id"

    baseline_id = fields.Many2one(
        comodel_name="project.baseline",
        index=True,
        required=True,
        ondelete="cascade",
    )
    project_id = fields.Many2one(
        related="baseline_id.project_id",
    )
    task_id = fields.Many2one(
        comodel_name="project.task",
        index=True,
        ondelete="set null",
        help="Link to the original task (may be deleted since snapshot).",
    )
    task_name = fields.Char(
        string="Task Name (snapshot)",
        required=True,
    )
    sequence = fields.Integer(default=10)
    date_planned_start = fields.Datetime(string="Planned Start (snapshot)")
    date_planned_end = fields.Datetime(string="Planned End (snapshot)")
    planned_hours = fields.Float(string="Planned Hours (snapshot)")
    milestone_id = fields.Many2one(
        comodel_name="project.milestone",
        string="Milestone (snapshot)",
        ondelete="set null",
    )
    step_id = fields.Many2one(
        comodel_name="project.workflow.step",
        string="Step (snapshot)",
        ondelete="set null",
    )
