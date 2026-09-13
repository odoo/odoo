from odoo import Command, api, fields, models

from ..tools import debug_log as dbg
from .project_task import CLOSED_STATES, DELIVERED_STATES


class ProjectHistory(models.Model):
    _name = "project.history"
    _description = "Project History"
    _order = "date_completed desc, id desc"

    project_id = fields.Many2one(
        comodel_name="project.project",
        index=True,
        ondelete="set null",
        help="Link to the original project (may be archived or deleted).",
    )
    name = fields.Char(
        string="Project Name (snapshot)",
        required=True,
        help="Frozen project name at time of archival.",
    )
    date_completed = fields.Date(required=True)
    date_start = fields.Date(string="Date Started")
    planned_duration_days = fields.Integer(
        string="Planned Duration (days)",
        help="Days from date_start to planned end date.",
    )
    actual_duration_days = fields.Integer(
        string="Actual Duration (days)",
        help="Days from date_start to actual completion.",
    )
    duration_variance_pct = fields.Float(
        string="Duration Variance %",
        export_string_translation=False,
        compute="_compute_variances",
        store=True,
        help="(actual - planned) / planned * 100. Positive = over-schedule.",
    )
    planned_hours = fields.Float(string="Planned Hours (sum of task.planned_hours)")
    actual_hours = fields.Float(
        help="Sum of effective_hours (requires timesheet module)."
    )
    hours_variance_pct = fields.Float(
        string="Hours Variance %",
        export_string_translation=False,
        compute="_compute_variances",
        store=True,
        help="(actual - planned) / planned * 100. Positive = over-budget.",
    )
    task_count = fields.Integer(string="Total Tasks")
    team_size = fields.Integer(string="Team Size (distinct assignees)")
    tag_ids = fields.Many2many(
        comodel_name="project.tags",
        relation="project_history_tags_rel",
        column1="history_id",
        column2="tag_id",
        string="Tags",
        help="Copied from project tags for reference class search.",
    )
    avg_lead_time = fields.Float(
        string="Avg Lead Time (hours)",
        help="Average lead_time_hours (create→end) at project completion.",
    )
    avg_cycle_time = fields.Float(
        string="Avg Cycle Time (hours)",
        help="Average cycle_time_hours (assign→end) at project completion.",
    )
    deadline_compliance_pct = fields.Float(
        string="Deadline Compliance %",
        help="Percentage of tasks that met their deadlines.",
    )

    @api.depends(
        "planned_duration_days",
        "actual_duration_days",
        "planned_hours",
        "actual_hours",
    )
    def _compute_variances(self) -> None:
        for rec in self:
            if rec.planned_duration_days:
                rec.duration_variance_pct = (
                    (rec.actual_duration_days - rec.planned_duration_days)
                    / rec.planned_duration_days
                    * 100
                )
            else:
                rec.duration_variance_pct = 0.0
            if rec.planned_hours:
                rec.hours_variance_pct = (
                    (rec.actual_hours - rec.planned_hours) / rec.planned_hours * 100
                )
            else:
                rec.hours_variance_pct = 0.0

    @dbg.timed
    @api.model
    def create_from_project(self, project) -> ProjectHistory:
        task_domain = [
            ("project_id", "=", project.id),
            ("is_template", "=", False),
        ]
        Task = self.env["project.task"]
        tasks = Task.search(task_domain)

        assignees = set()
        for task in tasks:
            assignees.update(task.user_ids.ids)

        planned_days = 0
        if project.date_start and project.date:
            planned_days = (project.date - project.date_start).days

        closed_tasks = tasks.filtered(lambda t: t.state in CLOSED_STATES)
        closed_dates = closed_tasks.filtered("date_closed").mapped("date_closed")
        completion_date = (
            max(closed_dates).date() if closed_dates else fields.Date.today()
        )

        actual_days = 0
        if project.date_start:
            actual_days = (completion_date - project.date_start).days

        planned_hours = sum(tasks.mapped("planned_hours"))

        actual_hours = 0.0
        if "effective_hours" in Task._fields:
            actual_hours = sum(tasks.mapped("effective_hours"))
        delivered_tasks = tasks.filtered(lambda t: t.state in DELIVERED_STATES)
        avg_lt = 0.0
        avg_ct = 0.0
        if delivered_tasks:
            lt_values = [
                t.lead_time_hours for t in delivered_tasks if t.lead_time_hours
            ]
            avg_lt = sum(lt_values) / len(lt_values) if lt_values else 0.0
            ct_values = [
                t.cycle_time_hours for t in delivered_tasks if t.cycle_time_hours
            ]
            avg_ct = sum(ct_values) / len(ct_values) if ct_values else 0.0

        dl_tasks = delivered_tasks.filtered("date_end")
        dl_pct = 0.0
        if dl_tasks:
            met = dl_tasks.filtered(
                lambda t: t.date_closed and t.date_closed <= t.date_end
            )
            dl_pct = len(met) / len(dl_tasks) * 100

        dbg.logic.debug(
            "project.history.create_from_project [project:%s]: tasks=%d closed=%d "
            "delivered=%d planned_days=%s actual_days=%s planned_h=%.1f "
            "actual_h=%.1f lead=%.1f cycle=%.1f deadline_pct=%.1f",
            project.id,
            len(tasks),
            len(closed_tasks),
            len(delivered_tasks),
            planned_days,
            actual_days,
            planned_hours,
            actual_hours,
            avg_lt,
            avg_ct,
            dl_pct,
        )
        return self.create(
            {
                "project_id": project.id,
                "name": project.name,
                "date_completed": completion_date,
                "date_start": project.date_start,
                "planned_duration_days": planned_days,
                "actual_duration_days": actual_days,
                "planned_hours": planned_hours,
                "actual_hours": actual_hours,
                "task_count": len(tasks),
                "team_size": len(assignees),
                "tag_ids": [Command.set(project.tag_ids.ids)],
                "avg_lead_time": avg_lt,
                "avg_cycle_time": avg_ct,
                "deadline_compliance_pct": dl_pct,
            }
        )
