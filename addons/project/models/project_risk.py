from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..tools import debug_log as dbg


class ProjectRisk(models.Model):
    _name = "project.risk"
    _description = "Project Risk"
    _order = "risk_score desc, id desc"
    _inherit = ["mixin.mail.thread"]

    name = fields.Char(
        string="Risk",
        required=True,
        tracking=True,
    )
    description = fields.Html()
    project_id = fields.Many2one(
        comodel_name="project.project",
        index=True,
        required=True,
        ondelete="cascade",
    )
    task_id = fields.Many2one(
        comodel_name="project.task",
        string="Related Task",
        index="btree_not_null",
        help="Optional link to a specific task affected by this risk.",
    )
    category = fields.Selection(
        selection=[
            ("technical", "Technical"),
            ("organizational", "Organizational"),
            ("external", "External"),
            ("financial", "Financial"),
            ("schedule", "Schedule"),
        ],
        default="technical",
        required=True,
        tracking=True,
    )
    probability = fields.Selection(
        selection=[
            ("1", "Rare"),
            ("2", "Unlikely"),
            ("3", "Possible"),
            ("4", "Likely"),
            ("5", "Almost Certain"),
        ],
        default="3",
        required=True,
        tracking=True,
    )
    impact = fields.Selection(
        selection=[
            ("1", "Negligible"),
            ("2", "Minor"),
            ("3", "Moderate"),
            ("4", "Major"),
            ("5", "Catastrophic"),
        ],
        default="3",
        required=True,
        tracking=True,
    )
    risk_score = fields.Integer(
        compute="_compute_risk_score_and_level",
        store=True,
        help="Probability × Impact (1–25).",
    )
    risk_level = fields.Selection(
        selection=[
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        compute="_compute_risk_score_and_level",
        store=True,
    )
    response_strategy = fields.Selection(
        selection=[
            ("mitigate", "Mitigate"),
            ("transfer", "Transfer"),
            ("accept", "Accept"),
            ("avoid", "Avoid"),
            ("exploit", "Exploit"),
        ],
        tracking=True,
    )
    response_plan = fields.Html()
    owner_id = fields.Many2one(
        comodel_name="res.users",
        string="Risk Owner",
        tracking=True,
        help="Person responsible for monitoring and responding to this risk.",
    )
    state = fields.Selection(
        selection=[
            ("identified", "Identified"),
            ("assessed", "Assessed"),
            ("mitigated", "Mitigated"),
            ("resolved", "Resolved"),
            ("accepted", "Accepted"),
        ],
        default="identified",
        required=True,
        tracking=True,
    )
    date_identified = fields.Date(default=fields.Date.today)
    date_resolved = fields.Date()
    active = fields.Boolean(default=True)

    @api.constrains("state", "date_resolved")
    def _check_date_resolved(self) -> None:
        for risk in self:
            if risk.state == "resolved" and not risk.date_resolved:
                raise ValidationError(
                    _("A resolved risk must have its resolution date set.")
                )

    @api.depends("probability", "impact")
    def _compute_risk_score_and_level(self) -> None:
        for risk in self:
            score = int(risk.probability or 0) * int(risk.impact or 0)
            risk.risk_score = score
            if score >= 16:
                risk.risk_level = "critical"
            elif score >= 10:
                risk.risk_level = "high"
            elif score >= 5:
                risk.risk_level = "medium"
            else:
                risk.risk_level = "low"
            dbg.logic.debug(
                "project.risk score %s: p=%s x i=%s = %d -> %s",
                dbg.rec(risk),
                risk.probability,
                risk.impact,
                score,
                risk.risk_level,
            )
