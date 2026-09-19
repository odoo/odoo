import textwrap
from typing import Any

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import SQL, float_is_zero


class SurveyUser_InputLine(models.Model):
    """One answered line within a survey.user_input."""

    _name = "survey.user_input.line"
    _description = "Survey User Input Line"
    _rec_name = "user_input_id"
    _order = "question_sequence, id"

    user_input_id = fields.Many2one(
        comodel_name="survey.user_input",
        index=True,
        required=True,
        ondelete="cascade",
    )
    survey_id = fields.Many2one(
        related="user_input_id.survey_id",
        string="Survey",
        readonly=False,
    )
    question_id = fields.Many2one(
        comodel_name="survey.question",
        index=True,
        required=True,
        ondelete="cascade",
    )
    page_id = fields.Many2one(
        related="question_id.page_id",
        string="Section",
        readonly=False,
    )
    question_sequence = fields.Integer(
        related="question_id.sequence",
        string="Sequence",
    )
    lang_id = fields.Many2one(
        comodel_name="res.lang",
        related="user_input_id.lang_id",
    )
    skipped = fields.Boolean()
    answer_type = fields.Selection(
        selection=[
            ("text_box", "Free Text"),
            ("char_box", "Text"),
            ("numerical_box", "Number"),
            ("scale", "Scale value"),
            ("date", "Date"),
            ("datetime", "Datetime"),
            ("suggestion", "Suggestion"),
        ]
    )
    value_char_box = fields.Char(string="Text answer")
    value_numerical_box = fields.Float(string="Numerical answer")
    value_scale = fields.Integer(string="Scale value")
    value_date = fields.Date(string="Date answer")
    value_datetime = fields.Datetime(string="Datetime answer")
    value_text_box = fields.Text(string="Free Text answer")
    suggested_answer_id = fields.Many2one(
        comodel_name="survey.question.answer",
        string="Suggested answer",
        ondelete="cascade",
    )
    matrix_row_id = fields.Many2one(
        comodel_name="survey.question.answer",
        string="Row answer",
        ondelete="cascade",
    )
    answer_score = fields.Float(
        string="Score",
        compute="_compute_answer_scoring",
        precompute=True,
        store=True,
    )
    answer_is_correct = fields.Boolean(
        string="Correct",
        compute="_compute_answer_scoring",
        precompute=True,
        store=True,
    )

    @api.depends(
        "answer_type",
        "value_text_box",
        "value_numerical_box",
        "value_char_box",
        "value_date",
        "value_datetime",
        "suggested_answer_id.value",
        "matrix_row_id.value",
    )
    def _compute_display_name(self) -> None:
        for line in self:
            if line.answer_type == "char_box":
                line.display_name = line.value_char_box
            elif line.answer_type == "text_box" and line.value_text_box:
                line.display_name = textwrap.shorten(
                    line.value_text_box, width=50, placeholder=" [...]"
                )
            elif line.answer_type == "numerical_box":
                line.display_name = line.value_numerical_box
            elif line.answer_type == "date":
                line.display_name = fields.Date.to_string(line.value_date)
            elif line.answer_type == "datetime":
                line.display_name = fields.Datetime.to_string(
                    fields.Datetime.context_timestamp(
                        self.env.user, line.value_datetime
                    )
                )
            elif line.answer_type == "scale":
                line.display_name = line.value_scale
            elif line.answer_type == "suggestion":
                if line.matrix_row_id:
                    line.display_name = (
                        f"{line.suggested_answer_id.value}: {line.matrix_row_id.value}"
                    )
                else:
                    line.display_name = line.suggested_answer_id.value

            if not line.display_name:
                line.display_name = _("Skipped")

    @api.depends(
        "answer_type",
        "value_text_box",
        "value_numerical_box",
        "value_scale",
        "value_date",
        "value_datetime",
        "suggested_answer_id",
        "suggested_answer_id.answer_score",
        "suggested_answer_id.is_correct",
        "question_id.question_type",
        "question_id.answer_score",
        "question_id.answer_numerical_box",
        "question_id.answer_date",
        "question_id.answer_datetime",
        "user_input_id",
    )
    def _compute_answer_scoring(self) -> None:
        for line in self:
            answer_is_correct, answer_score = False, 0
            if line.answer_type:
                if line.question_id.question_type in [
                    "simple_choice",
                    "dropdown",
                    "multiple_choice",
                ]:
                    if line.answer_type == "suggestion" and line.suggested_answer_id:
                        answer_score = line.suggested_answer_id.answer_score
                        answer_is_correct = line.suggested_answer_id.is_correct
                elif line.question_id.question_type in [
                    "date",
                    "datetime",
                    "numerical_box",
                ]:
                    answer = line[f"value_{line.answer_type}"]
                    if line.answer_type == "numerical_box":
                        answer = float(answer)
                    elif line.answer_type == "date":
                        answer = fields.Date.from_string(answer)
                    elif line.answer_type == "datetime":
                        answer = fields.Datetime.from_string(answer)
                    if (
                        answer is not None
                        and answer is not False
                        and answer == line.question_id[f"answer_{line.answer_type}"]
                    ):
                        answer_is_correct = True
                        answer_score = line.question_id.answer_score

            if (
                answer_score > 0
                and line.user_input_id.survey_id.session_speed_rating
                and line.user_input_id.is_session_answer
                and line.question_id.is_time_limited
            ):
                max_score_delay = 2
                time_limit = line.question_id.time_limit
                answered_at = line.create_date or self.env.cr.now()
                seconds_to_answer = (
                    answered_at
                    - line.user_input_id.survey_id.session_question_start_time
                ).total_seconds()
                question_remaining_time = time_limit - seconds_to_answer
                if (
                    question_remaining_time < 0
                    or line.question_id
                    != line.user_input_id.survey_id.session_question_id
                ):
                    answer_score /= 2
                elif seconds_to_answer > max_score_delay:
                    score_proportion = (time_limit - seconds_to_answer) / (
                        time_limit - max_score_delay
                    )
                    answer_score = (answer_score / 2) * (1 + score_proportion)

            line.answer_is_correct = answer_is_correct
            line.answer_score = answer_score

    @api.constrains(
        "user_input_id", "question_id", "suggested_answer_id", "matrix_row_id"
    )
    def _check_detached_answer(self):
        detached = self.filtered(lambda line: not line.user_input_id.survey_id)
        questions = detached.question_id
        choices = detached.suggested_answer_id | detached.matrix_row_id
        # A row lock alone leaves a REPEATABLE READ deleter's snapshot stale.
        # Version the parents without changing their business fields so a racing
        # move/delete retries instead of cascading away a newly recorded answer.
        for parents in (detached.user_input_id, questions, choices):
            if parents:
                self.env.cr.execute(
                    SQL(
                        "UPDATE %s SET id = id WHERE id = ANY(%s)",
                        SQL.identifier(parents._table),
                        parents.ids,
                    )
                )
        detached.user_input_id.invalidate_recordset(
            ["survey_id", "predefined_question_ids"]
        )
        questions.invalidate_recordset(["survey_id"])
        choices.invalidate_recordset(["question_id", "matrix_question_id"])
        for line in self:
            if not line.user_input_id.survey_id:
                if (
                    line.question_id.survey_id
                    or line.question_id
                    not in line.user_input_id.predefined_question_ids
                ):
                    raise ValidationError(
                        self.env._("This question does not belong to the response.")
                    )
                if (
                    line.suggested_answer_id
                    and line.suggested_answer_id.question_id != line.question_id
                ):
                    raise ValidationError(
                        self.env._("This answer does not belong to the question.")
                    )
                if (
                    line.matrix_row_id
                    and line.matrix_row_id.matrix_question_id != line.question_id
                ):
                    raise ValidationError(
                        self.env._("This matrix row does not belong to the question.")
                    )

    @api.constrains("skipped", "answer_type")
    def _check_answer_type_skipped(self) -> None:
        for line in self:
            if line.skipped == bool(line.answer_type):
                raise ValidationError(
                    _("A question can either be skipped or answered, not both.")
                )

            if line.answer_type == "numerical_box" and float_is_zero(
                line["value_numerical_box"], precision_digits=6
            ):
                continue
            if line.answer_type == "scale" and line["value_scale"] == 0:
                continue

            if line.answer_type == "suggestion":
                field_name = "suggested_answer_id"
            elif line.answer_type:
                field_name = f"value_{line.answer_type}"
            else:
                field_name = False

            if field_name and not line[field_name]:
                raise ValidationError(_("The answer must be in the right type"))

    def _get_domain_answer_matching(self) -> list[Any] | None:
        self.check_singleton()
        if self.answer_type in (
            "char_box",
            "text_box",
            "numerical_box",
            "scale",
            "date",
            "datetime",
        ):
            value_field = {
                "char_box": "value_char_box",
                "text_box": "value_text_box",
                "numerical_box": "value_numerical_box",
                "scale": "value_scale",
                "date": "value_date",
                "datetime": "value_datetime",
            }
            operators = {
                "char_box": "ilike",
                "text_box": "ilike",
                "numerical_box": "=",
                "scale": "=",
                "date": "=",
                "datetime": "=",
            }
            return [
                "&",
                ("question_id", "=", self.question_id.id),
                (
                    value_field[self.answer_type],
                    operators[self.answer_type],
                    self._get_answer_value(),
                ),
            ]
        elif self.answer_type == "suggestion":
            return self.suggested_answer_id._get_domain_answer_matching(
                self.matrix_row_id.id if self.matrix_row_id else False
            )
        return None

    def _get_answer_value(self) -> Any:
        self.check_singleton()
        if self.answer_type == "char_box":
            return self.value_char_box
        elif self.answer_type == "text_box":
            return self.value_text_box
        elif self.answer_type == "numerical_box":
            return self.value_numerical_box
        elif self.answer_type == "scale":
            return self.value_scale
        elif self.answer_type == "date":
            return self.value_date
        elif self.answer_type == "datetime":
            return self.value_datetime
        elif self.answer_type == "suggestion":
            return self.suggested_answer_id.value
        return None
