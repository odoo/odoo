from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..tools import debug_log as dbg


class ProjectGate(models.Model):
    _name = "project.gate"
    _description = "Project Gate Review"
    _order = "sequence, id"
    _inherit = ["mixin.mail.thread"]

    name = fields.Char("Gate Name", required=True, tracking=True)
    project_id = fields.Many2one(
        "project.project",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer("Gate Order", default=10)
    milestone_id = fields.Many2one(
        "project.milestone",
        string="Trigger Milestone",
        domain="[('project_id', '=', project_id)]",
        help="Review is triggered when this milestone is reached.",
    )
    criterion_ids = fields.One2many(
        "project.gate.criterion",
        "gate_id",
        string="Review Criteria",
    )
    state = fields.Selection(
        [
            ("pending", "Pending"),
            ("passed", "Passed"),
            ("failed", "Failed"),
            ("deferred", "Deferred"),
        ],
        default="pending",
        required=True,
        tracking=True,
    )
    date_review = fields.Date("Review Date", tracking=True)
    reviewer_ids = fields.Many2many(
        "res.users",
        string="Reviewers",
    )
    decision_notes = fields.Html()
    kill_criteria = fields.Html(
        help="Pre-defined conditions under which the project should be cancelled.",
    )
    criteria_met_count = fields.Integer(
        "Criteria Met",
        compute="_compute_criteria_met_count",
        export_string_translation=False,
    )
    criteria_total_count = fields.Count(
        "criterion_ids",
        "Total Criteria",
        export_string_translation=False,
    )

    @api.depends("criterion_ids.is_met")
    def _compute_criteria_met_count(self) -> None:
        for gate in self:
            gate.criteria_met_count = len(gate.criterion_ids.filtered("is_met"))
            dbg.logic.debug(
                "project.gate criteria %s: %d met of %d (state=%s)",
                dbg.rec(gate),
                gate.criteria_met_count,
                len(gate.criterion_ids),
                gate.state,
            )

    @api.constrains("milestone_id", "project_id")
    def _check_milestone_project(self) -> None:
        for gate in self:
            if gate.milestone_id and gate.milestone_id.project_id != gate.project_id:
                raise ValidationError(
                    self.env._(
                        "The trigger milestone of gate %(gate)s must belong to "
                        "its project (%(project)s).",
                        gate=gate.name,
                        project=gate.project_id.display_name,
                    )
                )


class ProjectGateCriterion(models.Model):
    _name = "project.gate.criterion"
    _description = "Gate Review Criterion"
    _order = "sequence, id"

    gate_id = fields.Many2one(
        "project.gate",
        required=True,
        ondelete="cascade",
        index=True,
    )
    name = fields.Char("Criterion", required=True)
    sequence = fields.Integer(default=10)
    is_met = fields.Boolean("Met", default=False)
    evidence = fields.Text()
