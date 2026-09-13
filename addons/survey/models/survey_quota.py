from typing import Self

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class SurveyQuota(models.Model):
    _name = "survey.quota"
    _description = "Survey Quota"
    _order = "survey_id, question_id, id"

    survey_id = fields.Many2one(
        comodel_name="survey.survey",
        index="btree_not_null",
        required=True,
        ondelete="cascade",
    )
    question_id = fields.Many2one(
        comodel_name="survey.question",
        required=True,
        domain="[('survey_id', '=', survey_id), ('question_type', 'in', ['simple_choice', 'multiple_choice'])]",
        ondelete="cascade",
    )
    answer_id = fields.Many2one(
        comodel_name="survey.question.answer",
        required=True,
        domain="[('question_id', '=', question_id)]",
        ondelete="cascade",
    )
    limit = fields.Integer(
        string="Quota Limit",
        default=100,
        required=True,
        help="Maximum number of responses that can select this answer. A response in "
        "progress reserves its place so the quota cannot be oversold, and releases it "
        "again if it is abandoned.",
    )
    current_count = fields.Integer(compute="_compute_quota_usage")
    is_full = fields.Boolean(
        string="Quota Full",
        compute="_compute_quota_usage",
    )
    active = fields.Boolean(default=True)

    RESERVATION_HOURS = 24

    _limit_positive = models.Constraint(
        'CHECK ("limit" > 0)',
        "Quota limit must be positive!",
    )

    @api.depends("survey_id", "answer_id", "limit")
    def _compute_quota_usage(self) -> None:
        counts = dict(
            self.env["survey.user_input.line"]._read_group(
                self._get_domain_usage(),
                ["suggested_answer_id"],
                ["user_input_id:count_distinct"],
            )
        )
        for quota in self:
            count = counts.get(quota.answer_id, 0)
            quota.current_count = count
            quota.is_full = count >= quota.limit

    def _get_domain_usage(self) -> list:
        """Completed responses, plus the ones still plausibly in flight.

        Counting every non-new response prevented overselling but never released
        the slot: an abandoned response held it for good, so anyone could exhaust a
        public survey's quotas by starting responses and closing the tab.
        """
        reserved_since = fields.Datetime.now() - relativedelta(
            hours=self.RESERVATION_HOURS
        )
        return [
            ("survey_id", "in", self.survey_id.ids),
            ("suggested_answer_id", "in", self.answer_id.ids),
            ("skipped", "=", False),
            ("user_input_id.test_entry", "=", False),
            "|",
            ("user_input_id.state", "=", "done"),
            "&",
            ("user_input_id.state", "=", "in_progress"),
            ("user_input_id.create_date", ">=", reserved_since),
        ]

    def _check_quota(self, answer_ids: list[int]) -> Self:
        if not self or not answer_ids:
            return self.browse()
        answer_ids = set(answer_ids)
        relevant = self.filtered(
            lambda quota: quota.active and quota.answer_id.id in answer_ids
        )
        if not relevant:
            return self.browse()
        self.env.cr.execute(
            "SELECT id FROM survey_quota WHERE id = ANY(%s) FOR UPDATE", [relevant.ids]
        )
        relevant.invalidate_recordset(["current_count", "is_full"])
        return relevant.filtered("is_full")
