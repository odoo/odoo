import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class SurveyFollowupRule(models.Model):
    _name = "survey.followup.rule"
    _description = "Survey Follow-up Rule"
    _order = "sequence, id"

    survey_id = fields.Many2one(
        comodel_name="survey.survey",
        index="btree_not_null",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(
        string="Rule Name",
        required=True,
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    condition_type = fields.Selection(
        selection=[
            ("always", "Always (on every completion)"),
            ("score_range", "Score in range"),
            ("passed", "Passed certification"),
            ("failed", "Failed certification"),
        ],
        string="Condition",
        default="always",
        required=True,
    )
    score_min = fields.Float(
        string="Min Score (%)",
        help="Minimum scoring_percentage to trigger (inclusive).",
    )
    score_max = fields.Float(
        string="Max Score (%)",
        default=100,
        help="Maximum scoring_percentage to trigger (inclusive).",
    )

    mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Email Template",
        required=True,
        domain="[('model', '=', 'survey.user_input')]",
        help="Email template to send. Available variables: object (survey.user_input).",
    )

    def _evaluate(self, user_input):
        self.check_singleton()
        if self.condition_type == "always":
            return True
        elif self.condition_type == "score_range":
            return self.score_min <= user_input.scoring_percentage <= self.score_max
        elif self.condition_type == "passed":
            return user_input.scoring_success
        elif self.condition_type == "failed":
            return not user_input.scoring_success
        return False

    def _execute(self, user_input):
        self.check_singleton()
        if not self._evaluate(user_input):
            return
        try:
            with self.env.cr.savepoint():
                self.mail_template_id.send_mail(
                    user_input.id,
                    force_send=False,
                )
            _logger.info(
                "Follow-up rule '%s' fired for input %s",
                self.name,
                user_input.id,
            )
        except Exception:
            _logger.warning(
                "Follow-up rule '%s' failed for input %s",
                self.name,
                user_input.id,
                exc_info=True,
            )
