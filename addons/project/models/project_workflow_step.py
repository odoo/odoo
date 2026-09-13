from datetime import timedelta
from typing import Any

from odoo import _, api, fields, models
from odoo.api import ValuesType
from odoo.exceptions import ValidationError

from ..tools import debug_log as dbg
from .project_task import CLOSED_STATES


class ProjectWorkflowStep(models.Model):
    _name = "project.workflow.step"
    _description = "Workflow Step"
    _inherit = ["mixin.project.pm"]
    _order = "sequence, id"

    def _default_project_ids(self) -> list[int] | None:
        default_project_id = self.env.context.get("default_project_id")
        return [default_project_id] if default_project_id else None

    active = fields.Boolean(
        export_string_translation=False,
        default=True,
    )
    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=1)
    project_ids = fields.Many2many(
        comodel_name="project.project",
        relation="project_workflow_step_project_rel",
        column1="step_id",
        column2="project_id",
        string="Projects",
        default=lambda self: self._default_project_ids(),
        help="Projects that use this workflow step. Steps can be shared across "
        "projects with similar processes to consolidate reporting.",
    )
    mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Email Template",
        domain=[("model", "=", "project.task")],
        help="Email sent automatically when a task enters this step.",
    )
    color = fields.Integer(export_string_translation=False)
    fold = fields.Boolean(string="Folded")
    task_state = fields.Selection(
        selection="_selection_task_states",
        help="When a task is moved into this step, its state is set to this "
        "value. Leave empty to keep the task's state untouched.",
    )
    rating_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Rating Email Template",
        domain=[("model", "=", "project.task")],
        help="Rating request sent automatically when a task enters this step, "
        "or at a regular interval while the task remains here.",
    )
    auto_update_state = fields.Boolean(
        string="Auto-update State on Rating",
        default=False,
        help="Automatically update the task state based on customer rating replies:\n"
        " * Good feedback → Approved (green bullet).\n"
        " * Neutral or bad feedback → Changes Requested (orange bullet).",
    )
    wip_limit = fields.Integer(
        string="WIP Limit",
        default=0,
        help="Maximum number of tasks allowed in this step per project. "
        "0 = no limit. When exceeded, the step header shows a warning.",
    )
    rotting_threshold_days = fields.Integer(
        string="Days to Rot",
        default=0,
        help="Number of days of inactivity before tasks in this step are marked "
        "as stale. Set to 0 to disable.",
    )
    date_rating_request = fields.Datetime(
        export_string_translation=False,
        help="Next scheduled periodic rating request. Seeded when periodic "
        "rating is enabled and advanced after each send — deliberately a "
        "plain field, not a now()-based compute that would reset on every "
        "module upgrade or unrelated recompute.",
    )
    rating_active = fields.Boolean(string="Send a Customer Rating Request")
    rating_status = fields.Selection(
        selection=[
            ("stage", "When reaching this step"),
            ("periodic", "On a periodic basis"),
        ],
        string="Customer Ratings Status",
        default="stage",
        required=True,
        help="When to send the rating request:\n"
        " * When reaching this step: sent once on step entry.\n"
        " * On a periodic basis: sent at the configured interval.",
    )
    rating_status_period = fields.Selection(
        selection=[
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("bimonthly", "Twice a Month"),
            ("monthly", "Once a Month"),
            ("quarterly", "Quarterly"),
            ("yearly", "Yearly"),
        ],
        string="Rating Frequency",
        default="monthly",
        required=True,
    )

    @dbg.timed
    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> ProjectWorkflowStep:
        dbg.lifecycle.debug(
            "project.workflow.step.create: %d vals, keys=%s",
            len(vals_list),
            dbg.vals_keys(vals_list),
        )
        records = super().create(vals_list)
        dbg.lifecycle.debug(
            "project.workflow.step.create: created %s", dbg.rec(records)
        )
        records._update_missing_rating_deadlines()
        return records

    @dbg.timed
    def write(self, vals: dict) -> bool:
        dbg.lifecycle.debug(
            "project.workflow.step.write on %s: keys=%s", dbg.rec(self), dbg.keys(vals)
        )
        res = super().write(vals)
        if {"rating_active", "rating_status", "rating_status_period"} & vals.keys():
            dbg.pipeline.debug(
                "[step:%s] write -> rating deadlines refresh", dbg.rec(self)
            )
            self._update_missing_rating_deadlines()
        return res

    def action_open_delete_wizard(self, stage_view: bool = False) -> dict[str, Any]:
        dbg.lifecycle.debug(
            "project.workflow.step.action_open_delete_wizard %s (projects %s, "
            "stage_view=%s)",
            dbg.rec(self),
            self.project_ids.ids,
            stage_view,
        )
        wizard = self.env["project.workflow.step.delete.wizard"].create(
            {
                "project_ids": self.project_ids.ids,
                "step_ids": self.ids,
            }
        )
        context = dict(self.env.context, stage_view=stage_view)
        return {
            "name": _("Delete Workflow Step"),
            "view_mode": "form",
            "res_model": "project.workflow.step.delete.wizard",
            "views": [
                (
                    self.env.ref("project.view_project_workflow_step_delete_wizard").id,
                    "form",
                )
            ],
            "type": "ir.actions.act_window",
            "res_id": wizard.id,
            "target": "new",
            "context": context,
        }

    _RATING_PERIOD_DAYS = {
        "daily": 1,
        "weekly": 7,
        "bimonthly": 15,
        "monthly": 30,
        "quarterly": 90,
        "yearly": 365,
    }

    def _get_next_rating_deadline(self):
        self.check_singleton()
        return fields.Datetime.now() + timedelta(
            days=self._RATING_PERIOD_DAYS.get(self.rating_status_period, 0)
        )

    def _update_missing_rating_deadlines(self) -> None:
        for step in self:
            if (
                step.rating_active
                and step.rating_status == "periodic"
                and not step.date_rating_request
            ):
                step.date_rating_request = step._get_next_rating_deadline()
                dbg.logic.debug(
                    "_update_missing_rating_deadlines %s: seeded %s (%s)",
                    dbg.rec(step),
                    step.date_rating_request,
                    step.rating_status_period,
                )

    @dbg.timed
    @api.model
    def _send_rating_all(self) -> None:
        steps = self.search(
            [
                ("rating_active", "=", True),
                ("rating_status", "=", "periodic"),
                ("date_rating_request", "<=", fields.Datetime.now()),
            ]
        )
        dbg.lifecycle.debug(
            "project.workflow.step._send_rating_all: cron start, %d steps due",
            len(steps),
        )
        for step in steps:
            tasks = step._get_rating_tasks()
            dbg.pipeline.debug(
                "[step:%s] periodic rating -> %s", step.id, dbg.rec(tasks)
            )
            tasks._send_task_rating_mail()
            step.date_rating_request = step._get_next_rating_deadline()
            self.env.cr.commit()
        dbg.lifecycle.debug("project.workflow.step._send_rating_all: cron end")

    def _get_rating_tasks(self):
        self.check_singleton()
        return self.env["project.task"].search(
            [
                ("step_id", "=", self.id),
                ("state", "not in", list(CLOSED_STATES)),
            ]
        )

    def _selection_task_states(self) -> list[tuple[str, str]]:
        return (
            self.env["project.task"]._fields["state"]._description_selection(self.env)
        )

    @api.constrains("task_state")
    def _check_task_state_in_selection(self) -> None:
        valid_keys = {key for key, _label in self._selection_task_states()}
        for step in self:
            if step.task_state and step.task_state not in valid_keys:
                raise ValidationError(
                    self.env._(
                        "Step %(step)s has task_state=%(value)s, which is not a "
                        "valid project.task.state value.",
                        step=step.display_name,
                        value=step.task_state,
                    )
                )
