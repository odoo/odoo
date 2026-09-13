from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

from ..tools import debug_log as dbg
from .project_task import CLOSED_STATES


class ProjectSprint(models.Model):
    _name = "project.sprint"
    _description = "Sprint"
    _order = "date_start desc, id desc"
    _inherit = ["mixin.mail.thread"]

    name = fields.Char("Sprint Name", required=True, tracking=True)
    project_id = fields.Many2one(
        "project.project",
        required=True,
        ondelete="cascade",
        index=True,
    )
    date_start = fields.Date("Start Date", required=True, tracking=True)
    date_end = fields.Date("End Date", required=True, tracking=True)
    goal = fields.Text(
        "Sprint Goal",
        help="One-sentence description of what this sprint aims to achieve.",
    )
    state = fields.Selection(
        [
            ("planning", "Planning"),
            ("active", "Active"),
            ("review", "Review"),
            ("closed", "Closed"),
        ],
        default="planning",
        required=True,
        tracking=True,
    )
    capacity_hours = fields.Float(
        "Team Capacity (hours)",
        help="Total team hours available for this sprint.",
    )
    task_ids = fields.One2many(
        "project.task",
        "sprint_id",
        string="Sprint Tasks",
    )
    task_count = fields.Integer(
        "Tasks",
        compute="_compute_task_metrics",
        export_string_translation=False,
    )
    completed_count = fields.Integer(
        "Completed",
        compute="_compute_task_metrics",
        export_string_translation=False,
    )
    completion_pct = fields.Float(
        "Completion %",
        compute="_compute_task_metrics",
        export_string_translation=False,
    )
    committed_hours = fields.Float(
        compute="_compute_task_metrics",
        help="Sum of planned_hours for all sprint tasks (PMI scope baseline).",
        export_string_translation=False,
    )
    velocity = fields.Float(
        "Velocity (hours)",
        compute="_compute_task_metrics",
        help="Sum of planned_hours for completed sprint tasks.",
        export_string_translation=False,
    )
    story_points_committed = fields.Float(
        compute="_compute_task_metrics",
        export_string_translation=False,
    )
    story_points_completed = fields.Float(
        compute="_compute_task_metrics",
        export_string_translation=False,
    )
    carried_over_count = fields.Integer(
        "Carried Over",
        readonly=True,
        copy=False,
        help="Tasks still unfinished when this sprint closed, returned to the "
        "backlog. Counted in the sprint's commitment, not in its velocity.",
    )
    carried_over_hours = fields.Float(
        readonly=True,
        copy=False,
        export_string_translation=False,
    )
    carried_over_story_points = fields.Float(
        readonly=True,
        copy=False,
        export_string_translation=False,
    )

    _sprint_date_check = models.Constraint(
        "check(date_end >= date_start)",
        "Sprint end date must be after start date.",
    )
    _unique_active_sprint = models.UniqueIndex(
        "(project_id) WHERE (state = 'active')",
        "A project can only have one active sprint at a time.",
    )

    @api.depends(
        "task_ids",
        "task_ids.state",
        "task_ids.planned_hours",
        "task_ids.story_points",
        "state",
        "carried_over_count",
        "carried_over_hours",
        "carried_over_story_points",
    )
    @dbg.timed
    def _compute_task_metrics(self) -> None:
        for sprint in self:
            tasks = sprint.task_ids
            closed = tasks.filtered(lambda t: t.state in CLOSED_STATES)
            carried = sprint.carried_over_count
            sprint.task_count = len(tasks) + carried
            sprint.completed_count = len(closed)
            sprint.completion_pct = (
                len(closed) / sprint.task_count * 100 if sprint.task_count else 0.0
            )
            sprint.committed_hours = (
                sum(tasks.mapped("planned_hours")) + sprint.carried_over_hours
            )
            sprint.velocity = sum(closed.mapped("planned_hours"))
            sprint.story_points_committed = (
                sum(tasks.mapped("story_points")) + sprint.carried_over_story_points
            )
            sprint.story_points_completed = sum(closed.mapped("story_points"))
            dbg.logic.debug(
                "sprint metrics [sprint:%s]: tasks=%d closed=%d carried=%d "
                "committed=%.1f velocity=%.1f",
                sprint.id,
                sprint.task_count,
                sprint.completed_count,
                carried,
                sprint.committed_hours,
                sprint.velocity,
            )

    def action_start(self) -> None:
        self.check_singleton()
        dbg.lifecycle.debug(
            "project.sprint.action_start [sprint:%s] project %s: %s -> active",
            self.id,
            self.project_id.id,
            self.state,
        )
        active_sprints = self.search(
            [
                ("project_id", "=", self.project_id.id),
                ("state", "=", "active"),
                ("id", "!=", self.id),
            ]
        )
        if active_sprints:
            raise ValidationError(
                _(
                    "Project '%(project)s' already has an active sprint: %(sprint)s",
                    project=self.project_id.name,
                    sprint=active_sprints[0].name,
                )
            )
        self.state = "active"

    def action_close(self) -> None:
        self.check_singleton()
        incomplete = self.task_ids.filtered(lambda t: t.state not in CLOSED_STATES)
        dbg.lifecycle.debug(
            "project.sprint.action_close [sprint:%s]: %s -> closed, carrying over %s",
            self.id,
            self.state,
            dbg.rec(incomplete),
        )
        self.write(
            {
                "carried_over_count": len(incomplete),
                "carried_over_hours": sum(incomplete.mapped("planned_hours")),
                "carried_over_story_points": sum(incomplete.mapped("story_points")),
                "state": "closed",
            }
        )
        if incomplete:
            incomplete.write({"sprint_id": False})
