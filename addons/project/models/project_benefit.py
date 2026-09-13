import logging

from odoo import api, fields, models

from ..tools import debug_log as dbg

_logger = logging.getLogger(__name__)


class ProjectBenefit(models.Model):
    _name = "project.benefit"
    _description = "Project Benefit"
    _order = "sequence, id"
    _inherit = ["mixin.mail.thread", "mixin.mail.activity"]

    name = fields.Char(
        string="Benefit",
        required=True,
        tracking=True,
    )
    sequence = fields.Integer(default=10)
    project_id = fields.Many2one(
        comodel_name="project.project",
        index=True,
        required=True,
        ondelete="cascade",
    )
    description = fields.Html(
        string="How This Benefit Will Be Realized",
        help="Describe the mechanism by which this benefit is expected to materialize.",
    )
    measurement_method = fields.Text(
        help="Specific, quantified method for measuring this benefit."
    )
    target_value = fields.Float()
    target_unit = fields.Char(
        string="Unit",
        help="Unit of measurement (e.g. %, $, hours, NPS score).",
    )
    actual_value = fields.Float()
    achievement_pct = fields.Float(
        string="Achievement %",
        export_string_translation=False,
        compute="_compute_achievement_pct",
        store=True,
        help="Actual / Target as a percentage.",
    )
    accountable_id = fields.Many2one(
        comodel_name="res.users",
        string="Accountable Owner",
        tracking=True,
        help="Business owner responsible for realizing and measuring this benefit.",
    )
    date_review = fields.Date(
        string="Next Review Date",
        help="When this benefit should next be reviewed for progress.",
    )
    date_review_reminder = fields.Date(
        string="Reminder Scheduled For",
        copy=False,
        help="Internal: the date_review for which a reminder activity was last "
        "scheduled by the cron. Prevents re-nagging every day once a reminder "
        "has been raised; a new reminder is only scheduled when date_review moves.",
    )
    state = fields.Selection(
        selection=[
            ("expected", "Expected"),
            ("tracking", "Tracking"),
            ("achieved", "Achieved"),
            ("partially", "Partially Achieved"),
            ("not_achieved", "Not Achieved"),
        ],
        default="expected",
        required=True,
        tracking=True,
    )
    notes = fields.Html(string="Review Notes")

    @dbg.timed
    @api.model
    def _cron_check_review_dates(self) -> None:
        today = fields.Date.context_today(self)
        benefits = self.search(
            [
                ("date_review", "<=", today),
                ("state", "in", ("expected", "tracking")),
                ("accountable_id", "!=", False),
            ]
        )
        due = len(benefits)
        benefits = benefits.filtered(lambda b: b.date_review_reminder != b.date_review)
        dbg.lifecycle.debug(
            "project.benefit._cron_check_review_dates: %d due, %d not yet reminded",
            due,
            len(benefits),
        )
        if not benefits:
            return

        activity_type = self.env.ref(
            "mail.mail_activity_data_todo", raise_if_not_found=False
        )
        if not activity_type:
            _logger.warning(
                "Benefit review cron: default activity type missing, skipping."
            )
            return
        scheduled = 0
        for benefit in benefits:
            benefit.activity_schedule(
                "mail.mail_activity_data_todo",
                date_deadline=benefit.date_review,
                summary=self.env._("Benefit review: %s", benefit.name),
                user_id=benefit.accountable_id.id,
            )
            benefit.date_review_reminder = benefit.date_review
            scheduled += 1
        _logger.info("Benefit review cron: scheduled %d activities", scheduled)

    @api.depends("target_value", "actual_value")
    def _compute_achievement_pct(self) -> None:
        for benefit in self:
            if benefit.target_value:
                benefit.achievement_pct = (
                    benefit.actual_value / benefit.target_value
                ) * 100
            else:
                benefit.achievement_pct = 0.0
