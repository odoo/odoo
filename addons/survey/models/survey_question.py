import contextlib
import logging
import random
from typing import Any, Self

from markupsafe import Markup

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.models import ValuesType

_logger = logging.getLogger(__name__)


class SurveyQuestion(models.Model):
    _name = "survey.question"
    _inherit = ["mixin.survey.question.statistics"]
    _description = "Survey Question"
    _rec_name = "title"
    _order = "sequence,id"

    @api.model
    def default_get(self, fields: list[str]) -> dict[str, Any]:
        res = super().default_get(fields)
        if default_survey_id := self.env.context.get("default_survey_id"):
            survey = self.env["survey.survey"].browse(default_survey_id)
            if "is_time_limited" in fields and "is_time_limited" not in res:
                res["is_time_limited"] = survey.session_speed_rating
            if "time_limit" in fields and "time_limit" not in res:
                res["time_limit"] = survey.session_speed_rating_time_limit
        return res

    active = fields.Boolean(default=True)
    char_box_type = fields.Selection(
        selection=[("text", "Text"), ("phone", "Phone")],
        default="text",
        required=True,
    )

    survey_id = fields.Many2one(
        comodel_name="survey.survey",
        index="btree_not_null",
        ondelete="cascade",
    )
    scoring_type = fields.Selection(
        related="survey_id.scoring_type",
        string="Scoring Type",
        readonly=True,
    )
    session_available = fields.Boolean(
        related="survey_id.session_available",
        string="Live Session available",
        readonly=True,
    )
    survey_session_speed_rating = fields.Boolean(
        related="survey_id.session_speed_rating"
    )
    survey_session_speed_rating_time_limit = fields.Integer(
        related="survey_id.session_speed_rating_time_limit",
        string="General Time limit (seconds)",
    )
    title = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=10)
    description = fields.Html(
        translate=True,
        sanitize=True,
        sanitize_overridable=True,
        help="Use this field to add additional explanations about your question or to "
        "illustrate it with pictures or a video.\n"
        "Write {{Q42}} to pipe in the respondent's answer to question 42 — the same "
        "question id a calculated field's Q42 refers to.",
    )
    question_placeholder = fields.Char(
        string="Placeholder",
        translate=True,
        compute="_compute_question_placeholder",
        store=True,
        readonly=False,
    )
    background_image = fields.Image(
        compute="_compute_background_image",
        store=True,
        readonly=False,
    )
    background_image_url = fields.Char(
        string="Background Url",
        compute="_compute_background_image_url",
    )

    is_page = fields.Boolean(string="Is a page?")
    question_ids = fields.One2many(
        comodel_name="survey.question",
        string="Questions",
        compute="_compute_question_ids",
    )
    questions_selection = fields.Selection(
        related="survey_id.questions_selection",
        readonly=True,
        help="If randomized is selected, add the number of random questions next to the section.",
    )
    random_questions_count = fields.Integer(
        string="# Questions Randomly Picked",
        default=1,
        help="Used on randomized sections to take X random questions from all the questions of that section.",
    )

    page_id = fields.Many2one(
        comodel_name="survey.question",
        compute="_compute_page_id",
        store=True,
    )
    question_type = fields.Selection(
        selection=[
            ("simple_choice", "Multiple choice: only one answer"),
            ("dropdown", "Dropdown"),
            ("multiple_choice", "Multiple choice: multiple answers allowed"),
            ("text_box", "Multiple Lines Text Box"),
            ("char_box", "Single Line Text Box"),
            ("numerical_box", "Numerical Value"),
            ("scale", "Scale"),
            ("nps", "Net Promoter Score"),
            ("slider", "Slider"),
            ("rating", "Rating"),
            ("ranking", "Ranking"),
            ("constant_sum", "Constant Sum"),
            ("file_upload", "File Upload"),
            ("date", "Date"),
            ("datetime", "Datetime"),
            ("matrix", "Matrix"),
            ("likert", "Likert Scale"),
            ("calculated", "Calculated / Hidden Field"),
            ("statement", "Statement / Info Screen"),
        ],
        compute="_compute_question_type",
        store=True,
        readonly=False,
    )
    is_scored_question = fields.Boolean(
        string="Scored",
        compute="_compute_is_scored_question",
        store=True,
        copy=True,
        readonly=False,
        help="Include this question as part of quiz scoring. Requires an answer and answer score to be taken into account.",
    )
    has_image_only_suggested_answer = fields.Boolean(
        string="Has image only suggested answer",
        compute="_compute_has_image_only_suggested_answer",
    )
    answer_numerical_box = fields.Float(
        string="Correct numerical answer",
        help="Correct number answer for this question.",
    )
    answer_date = fields.Date(
        string="Correct date answer",
        help="Correct date answer for this question.",
    )
    answer_datetime = fields.Datetime(
        string="Correct datetime answer",
        help="Correct date and time answer for this question.",
    )
    answer_score = fields.Float(
        string="Score",
        help="Score value for a correct answer to this question.",
    )
    save_as_email = fields.Boolean(
        string="Save as user email",
        compute="_compute_save_as_email",
        store=True,
        copy=True,
        readonly=False,
        help="If checked, this option will save the user's answer as its email address.",
    )
    save_as_nickname = fields.Boolean(
        string="Save as user nickname",
        compute="_compute_save_as_nickname",
        store=True,
        copy=True,
        readonly=False,
        help="If checked, this option will save the user's answer as its nickname.",
    )
    suggested_answer_ids = fields.One2many(
        comodel_name="survey.question.answer",
        inverse_name="question_id",
        string="Types of answers",
        copy=True,
        help="Labels used for proposed choices: simple choice, multiple choice and columns of matrix",
    )
    matrix_subtype = fields.Selection(
        selection=[
            ("simple", "One choice per row"),
            ("multiple", "Multiple choices per row"),
        ],
        string="Matrix Type",
        default="simple",
    )
    matrix_row_ids = fields.One2many(
        comodel_name="survey.question.answer",
        inverse_name="matrix_question_id",
        string="Matrix Rows",
        copy=True,
        help="Labels used for proposed choices: rows of matrix or Likert statements",
    )
    likert_preset = fields.Selection(
        selection=[
            ("agreement_5", "Agreement (5-point)"),
            ("agreement_7", "Agreement (7-point)"),
            ("frequency_5", "Frequency (5-point)"),
            ("satisfaction_5", "Satisfaction (5-point)"),
            ("importance_5", "Importance (5-point)"),
        ],
        help="Predefined scale labels. Select a preset then add your statements as matrix rows.",
    )
    scale_min = fields.Integer(
        string="Scale Minimum Value",
        default=0,
    )
    scale_max = fields.Integer(
        string="Scale Maximum Value",
        default=10,
    )
    scale_min_label = fields.Char(
        string="Scale Minimum Label",
        translate=True,
    )
    scale_mid_label = fields.Char(
        string="Scale Middle Label",
        translate=True,
    )
    scale_max_label = fields.Char(
        string="Scale Maximum Label",
        translate=True,
    )
    slider_min = fields.Float(
        string="Slider Minimum",
        default=0,
    )
    slider_max = fields.Float(
        string="Slider Maximum",
        default=100,
    )
    slider_step = fields.Float(default=1)
    slider_unit = fields.Char(
        help="Unit label displayed next to the value (e.g., '%', 'kg', '$')."
    )
    rating_max = fields.Integer(
        string="Rating Maximum",
        default=5,
        help="Number of rating icons (1 to 10).",
    )
    rating_icon = fields.Selection(
        selection=[("star", "Stars"), ("heart", "Hearts"), ("thumb", "Thumbs Up")],
        default="star",
    )
    constant_sum_total = fields.Integer(
        string="Total Points",
        default=100,
        help="The total that all distributed values must sum to.",
    )
    file_upload_types = fields.Char(
        string="Allowed File Types",
        default=".pdf,.doc,.docx,.jpg,.png",
        help="Comma-separated list of allowed file extensions.",
    )
    file_upload_max_size = fields.Integer(
        string="Max File Size (MB)",
        default=10,
        help="Maximum file size in megabytes.",
    )
    calculated_expression = fields.Char(
        string="Formula",
        help="Arithmetic expression using question references. Use Q<id> to reference "
        "other questions' numerical answers. Supports +, -, *, /, parentheses, and "
        "the functions: min(), max(), abs(), round().\n"
        "Example: Q42 * 0.3 + Q43 * 0.7",
    )
    is_time_limited = fields.Boolean(
        string="The question is limited in time",
        help="Currently only supported for live sessions.",
    )
    is_time_customized = fields.Boolean(string="Customized speed rewards")
    time_limit = fields.Integer(string="Time limit (seconds)")
    shuffle_answers = fields.Boolean(
        help="Randomize the display order of suggested answers for each respondent. "
        "The order is deterministic per respondent (seeded by their access token)."
    )
    comments_allowed = fields.Boolean(string="Show Comments Field")
    comments_message = fields.Char(
        string="Comment Message",
        translate=True,
    )
    comment_count_as_answer = fields.Boolean(string="Comment is an answer")
    validation_required = fields.Boolean(
        string="Validate entry",
        compute="_compute_validation_required",
        store=True,
        readonly=False,
    )
    validation_email = fields.Boolean(string="Input must be an email")
    validation_length_min = fields.Integer(
        string="Minimum Text Length",
        default=0,
    )
    validation_length_max = fields.Integer(
        string="Maximum Text Length",
        default=0,
    )
    validation_min_float_value = fields.Float(
        string="Minimum value",
        default=0.0,
    )
    validation_max_float_value = fields.Float(
        string="Maximum value",
        default=0.0,
    )
    validation_min_date = fields.Date(string="Minimum Date")
    validation_max_date = fields.Date(string="Maximum Date")
    validation_min_datetime = fields.Datetime(string="Minimum Datetime")
    validation_max_datetime = fields.Datetime(string="Maximum Datetime")
    validation_error_msg = fields.Char(
        string="Validation Error",
        translate=True,
    )
    constr_mandatory = fields.Boolean(string="Mandatory Answer")
    constr_error_msg = fields.Char(
        string="Error message",
        translate=True,
    )
    user_input_line_ids = fields.One2many(
        comodel_name="survey.user_input.line",
        inverse_name="question_id",
        string="Answers",
        domain=[("skipped", "=", False)],
        groups="survey.group_survey_user",
    )

    triggering_question_ids = fields.Many2many(
        comodel_name="survey.question",
        string="Triggering Questions",
        compute="_compute_triggering_question_ids",
        store=False,
        help="Questions containing the triggering answer(s) to display the current question.",
    )

    allowed_triggering_question_ids = fields.Many2many(
        comodel_name="survey.question",
        string="Allowed Triggering Questions",
        compute="_compute_triggering_questions",
        copy=False,
    )
    is_placed_before_trigger = fields.Boolean(
        string="Is misplaced?",
        compute="_compute_triggering_questions",
        help="Is this question placed before any of its trigger questions?",
    )
    triggering_answer_ids = fields.Many2many(
        comodel_name="survey.question.answer",
        string="Triggering Answers",
        copy=False,
        readonly=False,
        domain="""[
            ('question_id.survey_id', '=', survey_id),
            '&', ('question_id.question_type', 'in', ['simple_choice', 'dropdown', 'multiple_choice']),
                 '|',
                     ('question_id.sequence', '<', sequence),
                     '&', ('question_id.sequence', '=', sequence), ('question_id.id', '<', id)
        ]""",
        help="Picking any of these answers will trigger this question.\n"
        "Leave the field empty if the question should always be displayed.",
    )
    triggering_question_id = fields.Many2one(
        comodel_name="survey.question",
        string="Triggering Question (value-based)",
        domain="""[
            ('survey_id', '=', survey_id),
            ('is_page', '=', False),
            ('question_type', 'not in', ['simple_choice', 'dropdown', 'multiple_choice', 'matrix', 'statement']),
            '|', ('sequence', '<', sequence),
                 '&', ('sequence', '=', sequence), ('id', '<', id)
        ]""",
        ondelete="set null",
        help="Show this question only when the selected question's answer meets the operator condition.\n"
        "Use this for non-choice questions (numerical, text, date, scale, etc.).",
    )
    triggering_operator = fields.Selection(
        selection=[
            ("is_answered", "Is answered"),
            ("is_not_answered", "Is not answered"),
            ("eq", "Equals"),
            ("neq", "Does not equal"),
            ("gt", "Greater than"),
            ("gte", "Greater than or equal"),
            ("lt", "Less than"),
            ("lte", "Less than or equal"),
            ("contains", "Contains"),
        ],
        string="Trigger Operator",
        default="is_answered",
        help="Comparison operator for value-based conditional trigger.",
    )
    triggering_value = fields.Char(
        string="Trigger Value",
        help="The value to compare against. For numerical questions use a number, "
        "for date questions use YYYY-MM-DD format.",
    )

    _positive_len_min = models.Constraint(
        "CHECK (validation_length_min >= 0)",
        "A length must be positive!",
    )
    _positive_len_max = models.Constraint(
        "CHECK (validation_length_max >= 0)",
        "A length must be positive!",
    )
    _validation_length = models.Constraint(
        "CHECK (validation_length_min <= validation_length_max)",
        "Max length cannot be smaller than min length!",
    )
    _validation_float = models.Constraint(
        "CHECK (validation_min_float_value <= validation_max_float_value)",
        "Max value cannot be smaller than min value!",
    )
    _validation_date = models.Constraint(
        "CHECK (validation_min_date <= validation_max_date)",
        "Max date cannot be smaller than min date!",
    )
    _validation_datetime = models.Constraint(
        "CHECK (validation_min_datetime <= validation_max_datetime)",
        "Max datetime cannot be smaller than min datetime!",
    )
    _positive_answer_score = models.Constraint(
        "CHECK (answer_score >= 0)",
        "An answer score for a non-multiple choice question cannot be negative!",
    )
    _scored_datetime_have_answers = models.Constraint(
        "CHECK (is_scored_question != True OR question_type != 'datetime' OR answer_datetime is not null)",
        'All "Is a scored question = True" and "Question Type: Datetime" questions need an answer',
    )
    _scored_date_have_answers = models.Constraint(
        "CHECK (is_scored_question != True OR question_type != 'date' OR answer_date is not null)",
        'All "Is a scored question = True" and "Question Type: Date" questions need an answer',
    )
    _scale = models.Constraint(
        "CHECK (question_type != 'scale' OR (scale_min >= 0 AND scale_max <= 100 AND scale_min < scale_max AND (scale_max - scale_min) <= 20))",
        "The scale must be a growing non-empty range with min >= 0, max <= 100, and at most 20 steps",
    )
    _slider = models.Constraint(
        "CHECK (question_type != 'slider' OR (slider_min < slider_max AND slider_step > 0))",
        "Slider must have min < max and a positive step",
    )
    _rating = models.Constraint(
        "CHECK (question_type != 'rating' OR (rating_max >= 1 AND rating_max <= 10))",
        "Rating max must be between 1 and 10",
    )
    _constant_sum = models.Constraint(
        "CHECK (question_type != 'constant_sum' OR constant_sum_total > 0)",
        "Constant sum total must be positive",
    )
    _is_time_limited_have_time_limit = models.Constraint(
        "CHECK (is_time_limited != TRUE OR time_limit IS NOT NULL AND time_limit > 0)",
        "All time-limited questions need a positive time limit",
    )

    @api.constrains("is_page")
    def _check_question_type_for_pages(self) -> None:
        invalid_pages = self.filtered(
            lambda question: question.is_page and question.question_type
        )
        if invalid_pages:
            raise ValidationError(
                _(
                    "Question type should be empty for these pages: %s",
                    ", ".join(invalid_pages.mapped("title")),
                )
            )

    @api.constrains("triggering_answer_ids", "triggering_question_id")
    def _check_no_conditional_cycle(self) -> None:
        conditional = self.search(
            [
                ("survey_id", "in", self.survey_id.ids),
                "|",
                ("triggering_answer_ids", "!=", False),
                ("triggering_question_id", "!=", False),
            ]
        )
        triggered_by = {
            question.id: set(question.triggering_answer_ids.question_id.ids)
            | set(question.triggering_question_id.ids)
            for question in conditional
        }

        acyclic: set[int] = set()

        def _has_cycle(start_id: int) -> bool:
            path: list[int] = []
            on_path: set[int] = set()
            stack: list[tuple[int, bool]] = [(start_id, False)]
            while stack:
                node, leaving = stack.pop()
                if leaving:
                    on_path.discard(path.pop())
                    acyclic.add(node)
                    continue
                if node in on_path:
                    return True
                if node in acyclic:
                    continue
                path.append(node)
                on_path.add(node)
                stack.append((node, True))
                stack.extend((dep, False) for dep in triggered_by.get(node, ()))
            return False

        for question in conditional & self:
            if _has_cycle(question.id):
                raise ValidationError(
                    _(
                        "Circular dependency detected in conditional questions. "
                        "Question '%(title)s' is part of a trigger cycle.",
                        title=question.title,
                    )
                )

    @api.constrains(
        "survey_id", "is_page", "triggering_answer_ids", "triggering_question_id"
    )
    def _check_detached_question(self):
        for question in self:
            if not question.survey_id and (
                question.triggering_answer_ids or question.triggering_question_id
            ):
                raise ValidationError(
                    self.env._("Conditional questions require a survey.")
                )

    @api.constrains("survey_id")
    def _check_detached_question_history(self):
        groups = (
            self.env["survey.user_input.line"]
            .sudo()
            ._read_group(
                [("question_id", "in", self.ids)], ["question_id", "survey_id"]
            )
        )
        for question, survey in groups:
            if question.survey_id != survey and (not question.survey_id or not survey):
                raise ValidationError(
                    self.env._(
                        "Questions with recorded answers must keep their survey ownership."
                    )
                )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_detached_answers(self):
        detached = self.filtered(lambda question: not question.survey_id)
        if detached and self.env["survey.user_input.line"].sudo().search_count(
            [("question_id", "in", detached.ids)], limit=1
        ):
            raise UserError(
                self.env._(
                    "Archive questions with submitted answers instead of deleting them."
                )
            )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        questions = super().create(vals_list)
        questions.filtered(
            lambda q: (
                q.survey_id
                and (
                    q.survey_id.session_speed_rating != q.is_time_limited
                    or (
                        q.is_time_limited
                        and q.survey_id.session_speed_rating_time_limit != q.time_limit
                    )
                )
            )
        ).is_time_customized = True
        return questions

    def copy(self, default: ValuesType | None = None) -> Self:
        new_questions = super().copy(default)
        for old_question, new_question in zip(self, new_questions, strict=False):
            if old_question.triggering_answer_ids:
                new_question.triggering_answer_ids = old_question.triggering_answer_ids
        return new_questions

    @api.ondelete(at_uninstall=False)
    def _unlink_except_live_sessions_in_progress(self) -> None:
        running_surveys = self.survey_id.filtered(
            lambda survey: survey.session_state == "in_progress"
        )
        if running_surveys:
            raise UserError(
                _(
                    'You cannot delete questions from surveys "%(survey_names)s" while live sessions are in progress.',
                    survey_names=", ".join(running_surveys.mapped("title")),
                )
            )

    @api.depends("suggested_answer_ids", "suggested_answer_ids.value")
    def _compute_has_image_only_suggested_answer(self) -> None:
        questions_with_image_only_answer = self.env["survey.question"].search(
            [("id", "in", self.ids), ("suggested_answer_ids.value", "in", [False, ""])]
        )
        questions_with_image_only_answer.has_image_only_suggested_answer = True
        (
            self - questions_with_image_only_answer
        ).has_image_only_suggested_answer = False

    @api.depends("question_type")
    def _compute_question_placeholder(self) -> None:
        for question in self:
            if (
                question.question_type
                in (
                    "simple_choice",
                    "dropdown",
                    "multiple_choice",
                    "matrix",
                    "likert",
                    "calculated",
                    "statement",
                )
                or not question.question_placeholder
            ):
                question.question_placeholder = False

    @api.depends("is_page")
    def _compute_background_image(self) -> None:
        for question in self.filtered(lambda q: not q.is_page):
            question.background_image = False

    @api.depends(
        "survey_id.access_token",
        "background_image",
        "page_id",
        "survey_id.background_image_url",
    )
    def _compute_background_image_url(self) -> None:
        for question in self:
            if question.is_page:
                background_section_id = (
                    question.id if question.background_image else False
                )
            else:
                background_section_id = (
                    question.page_id.id if question.page_id.background_image else False
                )

            if background_section_id:
                survey_token = question.survey_id.access_token
                question.background_image_url = f"/survey/{survey_token}/{background_section_id}/get_background_image"
            else:
                question.background_image_url = question.survey_id.background_image_url

    @api.depends("is_page")
    def _compute_question_type(self) -> None:
        pages = self.filtered(lambda question: question.is_page)
        pages.question_type = False
        (self - pages).filtered(
            lambda question: not question.question_type
        ).question_type = "simple_choice"

    @api.depends(
        "survey_id.question_and_page_ids.is_page",
        "survey_id.question_and_page_ids.sequence",
    )
    def _compute_question_ids(self) -> None:
        for question in self:
            if question.is_page:
                question.question_ids = question.survey_id.question_ids.filtered(
                    lambda q, page=question: q.page_id == page
                ).sorted(lambda q: q._index())
            else:
                question.question_ids = self.env["survey.question"]

    @api.depends(
        "survey_id.question_and_page_ids.is_page",
        "survey_id.question_and_page_ids.sequence",
    )
    def _compute_page_id(self) -> None:
        for survey, questions in self.grouped("survey_id").items():
            page_by_question = {}
            page = None
            for q in survey.question_and_page_ids.sorted():
                if q.is_page:
                    page = q
                else:
                    page_by_question[q.id] = page
            for question in questions:
                question.page_id = (
                    None if question.is_page else page_by_question.get(question.id)
                )

    @api.depends("question_type", "validation_email")
    def _compute_save_as_email(self) -> None:
        for question in self:
            if question.question_type != "char_box" or not question.validation_email:
                question.save_as_email = False

    @api.depends("question_type")
    def _compute_save_as_nickname(self) -> None:
        for question in self:
            if question.question_type != "char_box":
                question.save_as_nickname = False

    @api.depends("question_type")
    def _compute_validation_required(self) -> None:
        for question in self:
            if not question.validation_required or question.question_type not in [
                "char_box",
                "numerical_box",
                "date",
                "datetime",
            ]:
                question.validation_required = False

    @api.depends("survey_id", "survey_id.question_ids", "triggering_answer_ids")
    def _compute_triggering_questions(self) -> None:
        possible_trigger_questions = self.search(
            [
                ("is_page", "=", False),
                (
                    "question_type",
                    "in",
                    ["simple_choice", "dropdown", "multiple_choice"],
                ),
                ("suggested_answer_ids", "!=", False),
                ("survey_id", "in", self.survey_id.ids),
            ]
        )
        (self | possible_trigger_questions).flush_recordset()
        self.env.cr.execute(
            "SELECT id, sequence FROM survey_question WHERE id =ANY(%s)", [self.ids]
        )
        conditional_questions_sequences = dict(self.env.cr.fetchall())

        for question in self:
            question_id = question._origin.id
            if not question_id:
                question.allowed_triggering_question_ids = (
                    possible_trigger_questions.filtered(
                        lambda q, survey_origin=question.survey_id._origin.id: (
                            q.survey_id.id == survey_origin
                        )
                    )
                )
                question.is_placed_before_trigger = False
                continue

            question_sequence = conditional_questions_sequences[question_id]

            question.allowed_triggering_question_ids = possible_trigger_questions.filtered(
                lambda q, survey_origin=question.survey_id._origin.id, seq=question_sequence, qid=question_id: (
                    q.survey_id.id == survey_origin
                    and (q.sequence < seq or (q.sequence == seq and q.id < qid))
                )
            )
            question.is_placed_before_trigger = bool(
                set(question.triggering_answer_ids.question_id.ids)
                - set(question.allowed_triggering_question_ids.ids)
            )

    @api.depends("triggering_answer_ids")
    def _compute_triggering_question_ids(self) -> None:
        for question in self:
            question.triggering_question_ids = (
                question.triggering_answer_ids.question_id
            )

    @api.depends(
        "question_type",
        "scoring_type",
        "answer_date",
        "answer_datetime",
        "answer_numerical_box",
        "suggested_answer_ids.is_correct",
    )
    def _compute_is_scored_question(self) -> None:
        for question in self:
            if question.scoring_type == "no_scoring":
                question.is_scored_question = False
            elif question.question_type == "date":
                question.is_scored_question = bool(question.answer_date)
            elif question.question_type == "datetime":
                question.is_scored_question = bool(question.answer_datetime)
            elif question.question_type == "numerical_box":
                question.is_scored_question = question.answer_score > 0
            elif question.question_type in [
                "simple_choice",
                "dropdown",
                "multiple_choice",
            ]:
                question.is_scored_question = any(
                    question.suggested_answer_ids.mapped("is_correct")
                )
            else:
                question.is_scored_question = False

    @api.onchange("question_type")
    def _onchange_validation_parameters(self) -> None:
        self.validation_email = False
        self.validation_length_min = 0
        self.validation_length_max = 0
        self.validation_min_date = False
        self.validation_max_date = False
        self.validation_min_datetime = False
        self.validation_max_datetime = False
        self.validation_min_float_value = 0
        self.validation_max_float_value = 0

    # What shape of payload each question type can be handed. /survey/submit is a
    # public jsonrpc route, so the value is whatever JSON the caller sent: without this
    # a crafted shape reached a validator that assumed otherwise and raised TypeError or
    # AttributeError out of the request -- an unauthenticated 500 per combination.
    _SCALAR_ANSWER_TYPES = (
        "char_box",
        "text_box",
        "numerical_box",
        "scale",
        "nps",
        "slider",
        "rating",
        "date",
        "datetime",
        "file_upload",
    )
    _MAPPING_ANSWER_TYPES = ("matrix", "likert", "ranking", "constant_sum")

    def _get_form_answers(self, form):
        answers = {}
        errors = {}
        for question in self:
            if question.question_type == "multiple_choice":
                answer = [
                    choice.id
                    for choice in question.suggested_answer_ids
                    if form.get(f"question_{question.id}_answer_{choice.id}")
                ]
            else:
                answer = form.get(f"question_{question.id}", "")
                if isinstance(answer, str):
                    answer = answer.strip()
            errors.update(question._check_answer(answer))
            if not question._is_unanswered(answer):
                answers[question.id] = answer
        if errors:
            raise ValidationError("\n".join(dict.fromkeys(errors.values())))
        return answers

    def _get_answers_description(self, answers):
        lines = []
        for question in self:
            answer = answers.get(question.id)
            if question._is_unanswered(answer):
                continue
            if question.question_type in (
                "dropdown",
                "simple_choice",
                "multiple_choice",
            ):
                ids = answer if isinstance(answer, list) else [answer]
                selected = {int(value) for value in ids}
                answer = ", ".join(
                    question.suggested_answer_ids.filtered(
                        lambda choice, ids=selected: choice.id in ids
                    ).mapped("value")
                )
            lines.append(
                Markup("<span>%s - %s</span>")
                % (question.title, Markup("<br/>").join(str(answer).splitlines()))
            )
        if not lines:
            return Markup("")
        return Markup("<br/><strong>%s</strong><br/>%s") % (
            self.env._("Questions & Answers"),
            Markup("<br/>").join(lines),
        )

    def _is_well_shaped_answer(self, answer: Any) -> bool:
        self.check_singleton()
        if self._is_unanswered(answer):
            return True
        if self.question_type in self._SCALAR_ANSWER_TYPES:
            return isinstance(answer, str | int | float) and not isinstance(
                answer, bool
            )
        if self.question_type in self._MAPPING_ANSWER_TYPES:
            return isinstance(answer, dict)
        if self.question_type in ("simple_choice", "dropdown", "multiple_choice"):
            # The form submits a comment as one `{"comment": text}` item among
            # the chosen answer ids; the controller lifts it out afterwards.
            candidates = answer if isinstance(answer, list) else [answer]
            return all(
                (isinstance(item, str | int) and not isinstance(item, bool))
                or (
                    isinstance(item, dict)
                    and set(item) == {"comment"}
                    and isinstance(item["comment"], str)
                )
                for item in candidates
            )
        return True

    def _check_answer(self, answer: Any, comment: str | None = None) -> dict[int, str]:
        self.check_singleton()
        if isinstance(answer, str):
            answer = answer.strip()
        if self.question_type in ("statement", "calculated"):
            return {}
        if not self._is_well_shaped_answer(answer):
            _logger.warning(
                "Survey %s: question %s was sent a %s, which it cannot answer with.",
                self.survey_id.id,
                self.id,
                type(answer).__name__,
            )
            return {self.id: _("This answer is not a valid choice for this question.")}
        if self._is_unanswered(answer) and self.question_type not in [
            "simple_choice",
            "dropdown",
            "multiple_choice",
        ]:
            if self.constr_mandatory and not self.survey_id.users_can_go_back:
                return {
                    self.id: self.constr_error_msg
                    or _("This question requires an answer.")
                }
        elif self.question_type == "char_box":
            return self._check_answer_char_box(answer)
        elif self.question_type == "numerical_box":
            return self._check_answer_numerical_box(answer)
        elif self.question_type in ["date", "datetime"]:
            return self._check_answer_date(answer)
        elif self.question_type in ["simple_choice", "dropdown", "multiple_choice"]:
            return self._check_answer_choice(answer, comment)
        elif self.question_type in ("matrix", "likert"):
            return self._check_answer_matrix(answer)
        elif self.question_type in ("scale", "nps"):
            return self._check_answer_scale(answer)
        elif self.question_type == "slider":
            return self._check_answer_slider(answer)
        elif self.question_type == "rating":
            return self._check_answer_rating(answer)
        elif self.question_type == "ranking":
            return self._check_answer_ranking(answer)
        elif self.question_type == "constant_sum":
            return self._check_answer_constant_sum(answer)
        elif self.question_type == "file_upload":
            return self._check_answer_file_upload(answer)
        return {}

    _ZERO_IS_AN_ANSWER = ("numerical_box", "slider", "scale", "nps", "rating")

    def _is_unanswered(self, answer: Any) -> bool:
        if (
            isinstance(answer, int | float)
            and not isinstance(answer, bool)
            and answer == 0
            and self.question_type in self._ZERO_IS_AN_ANSWER
        ):
            return False
        if isinstance(answer, str):
            return not answer.strip()
        return not answer

    def _check_answer_char_box(self, answer: str) -> dict[int, str]:
        answer = str(answer)
        if self.validation_email:
            if not tools.email_normalize(answer):
                return {self.id: _("This answer must be an email address")}

        if self.validation_required:
            if not (
                self.validation_length_min <= len(answer) <= self.validation_length_max
            ):
                return {
                    self.id: self.validation_error_msg
                    or _("The answer you entered is not valid.")
                }
        return {}

    def _check_answer_numerical_box(self, answer: Any) -> dict[int, str]:
        try:
            floatanswer = float(answer)
        except ValueError, TypeError:
            return {self.id: _("This is not a number")}

        if self.validation_required:
            with contextlib.suppress(TypeError, ValueError):
                if not (
                    self.validation_min_float_value
                    <= floatanswer
                    <= self.validation_max_float_value
                ):
                    return {
                        self.id: self.validation_error_msg
                        or _("The answer you entered is not valid.")
                    }
        return {}

    def _check_answer_date(self, answer: str) -> dict[int, str]:
        is_datetime = self.question_type == "datetime"
        field_class = fields.Datetime if is_datetime else fields.Date
        try:
            dateanswer = field_class.from_string(answer)
        except ValueError, TypeError:
            return {self.id: _("This is not a date")}
        if self.validation_required:
            if is_datetime:
                min_date = fields.Datetime.from_string(self.validation_min_datetime)
                max_date = fields.Datetime.from_string(self.validation_max_datetime)
            else:
                min_date = fields.Date.from_string(self.validation_min_date)
                max_date = fields.Date.from_string(self.validation_max_date)

            if (
                (min_date and max_date and not (min_date <= dateanswer <= max_date))
                or (min_date and not min_date <= dateanswer)
                or (max_date and not dateanswer <= max_date)
            ):
                return {
                    self.id: self.validation_error_msg
                    or _("The answer you entered is not valid.")
                }
        return {}

    def _check_answer_choice(self, answer: Any, comment: str | None) -> dict[int, str]:
        answers = answer if isinstance(answer, list) else ([answer] if answer else [])

        if foreign := self._filter_foreign_answer_ids(answers):
            return {self.id: self._answer_not_ours_error(foreign)}

        valid_answers_count = len(answers)
        if comment and self.comment_count_as_answer:
            valid_answers_count += 1

        if (
            valid_answers_count == 0
            and self.constr_mandatory
            and not self.survey_id.users_can_go_back
        ):
            return {
                self.id: self.constr_error_msg or _("This question requires an answer.")
            }

        if valid_answers_count > 1 and self.question_type in (
            "simple_choice",
            "dropdown",
        ):
            return {self.id: _("For this question, you can only select one answer.")}

        return {}

    def _check_answer_matrix(self, answers: dict[str, list[int]]) -> dict[int, str]:
        if answers:
            if foreign := self._filter_foreign_answer_ids(
                answers.keys(), field="matrix_row_ids"
            ):
                return {self.id: self._answer_not_ours_error(foreign)}
            submitted_columns = [
                column for columns in answers.values() for column in columns
            ]
            if foreign := self._filter_foreign_answer_ids(submitted_columns):
                return {self.id: self._answer_not_ours_error(foreign)}

        if (
            not self.survey_id.users_can_go_back
            and self.constr_mandatory
            and len(self.matrix_row_ids) != len(answers)
        ):
            return {
                self.id: self.constr_error_msg or _("This question requires an answer.")
            }
        return {}

    def _filter_foreign_answer_ids(
        self, answer_ids: Any, field: str = "suggested_answer_ids"
    ) -> list[Any]:
        self.check_singleton()
        own_ids = set(self[field].ids)
        foreign = []
        for answer_id in answer_ids:
            if not answer_id:
                continue
            try:
                candidate = int(answer_id)
            except ValueError, TypeError:
                foreign.append(answer_id)
                continue
            if candidate not in own_ids:
                foreign.append(answer_id)
        return foreign

    def _answer_not_ours_error(self, foreign: list[Any]) -> str:
        _logger.warning(
            "Survey %s: rejected %s answer id(s) not belonging to question %s: %s",
            self.survey_id.id,
            len(foreign),
            self.id,
            foreign,
        )
        return _("This answer is not a valid choice for this question.")

    def _check_answer_scale(self, answer: Any) -> dict[int, str]:
        if (
            not self.survey_id.users_can_go_back
            and self.constr_mandatory
            and self._is_unanswered(answer)
        ):
            return {
                self.id: self.constr_error_msg or _("This question requires an answer.")
            }
        return {}

    def _check_answer_slider(self, answer: Any) -> dict[int, str]:
        if self._is_unanswered(answer):
            if self.constr_mandatory and not self.survey_id.users_can_go_back:
                return {
                    self.id: self.constr_error_msg
                    or _("This question requires an answer.")
                }
            return {}
        try:
            val = float(answer)
        except ValueError, TypeError:
            return {self.id: _("Invalid numerical value.")}
        if val < self.slider_min or val > self.slider_max:
            return {
                self.id: _(
                    "Value must be between %(min)s and %(max)s.",
                    min=self.slider_min,
                    max=self.slider_max,
                )
            }
        return {}

    def _check_answer_rating(self, answer: Any) -> dict[int, str]:
        if self._is_unanswered(answer):
            if self.constr_mandatory and not self.survey_id.users_can_go_back:
                return {
                    self.id: self.constr_error_msg
                    or _("This question requires an answer.")
                }
            return {}
        try:
            val = int(answer)
        except ValueError, TypeError:
            return {self.id: _("Invalid rating value.")}
        if val < 1 or val > self.rating_max:
            return {self.id: _("Rating must be between 1 and %s.", self.rating_max)}
        return {}

    def _check_answer_ranking(self, answer: Any) -> dict[int, str]:
        if not answer:
            if self.constr_mandatory and not self.survey_id.users_can_go_back:
                return {
                    self.id: self.constr_error_msg
                    or _("This question requires an answer.")
                }
            return {}
        if not isinstance(answer, dict):
            return {self.id: _("Invalid ranking answer format.")}
        if len(answer) != len(self.suggested_answer_ids):
            return {self.id: _("Please rank all items.")}
        return {}

    def _check_answer_constant_sum(self, answer: Any) -> dict[int, str]:
        if not answer:
            if self.constr_mandatory and not self.survey_id.users_can_go_back:
                return {
                    self.id: self.constr_error_msg
                    or _("This question requires an answer.")
                }
            return {}
        if not isinstance(answer, dict):
            return {self.id: _("Invalid answer format.")}
        try:
            total = sum(float(v) for v in answer.values())
        except ValueError, TypeError:
            return {self.id: _("All values must be numbers.")}
        if abs(total - self.constant_sum_total) > 0.01:
            return {
                self.id: _(
                    "Values must sum to %(expected)s (currently %(total)s).",
                    expected=self.constant_sum_total,
                    total=total,
                )
            }
        return {}

    def _check_answer_file_upload(self, answer: Any) -> dict[int, str]:
        if not answer:
            if self.constr_mandatory and not self.survey_id.users_can_go_back:
                return {
                    self.id: self.constr_error_msg
                    or _("This question requires an answer.")
                }
            return {}
        try:
            attachment_id = int(answer)
        except ValueError, TypeError:
            return {self.id: _("Invalid file upload.")}
        attachment = self.env["ir.attachment"].sudo().browse(attachment_id).exists()
        if not attachment:
            return {self.id: _("Uploaded file not found.")}
        if self.file_upload_types:
            allowed = {
                ext.strip().lower()
                for ext in self.file_upload_types.split(",")
                if ext.strip()
            }
            fname = (attachment.name or "").lower()
            if allowed and not any(fname.endswith(ext) for ext in allowed):
                return {
                    self.id: _(
                        "File type not allowed. Accepted: %s", self.file_upload_types
                    )
                }
        if self.file_upload_max_size and attachment.file_size:
            max_bytes = self.file_upload_max_size * 1024 * 1024
            if attachment.file_size > max_bytes:
                return {
                    self.id: _(
                        "File exceeds maximum size of %s MB.", self.file_upload_max_size
                    )
                }
        return {}

    def _get_displayed_suggested_answers(self, seed_token: str = "") -> Any:
        self.check_singleton()
        answers = self.suggested_answer_ids
        if not self.shuffle_answers or not seed_token:
            return answers
        rng = random.Random(f"{seed_token}-{self.id}")
        answer_list = list(answers)
        rng.shuffle(answer_list)
        return self.env["survey.question.answer"].concat(*answer_list)

    def _get_max_obtainable_score(self) -> float:
        total = 0.0
        for question in self:
            positive_scores = [
                answer.answer_score
                for answer in question.suggested_answer_ids
                if answer.answer_score > 0
            ]
            if question.question_type in ("simple_choice", "dropdown"):
                total += max(positive_scores, default=0)
            elif question.question_type == "multiple_choice":
                total += sum(positive_scores)
            elif question.is_scored_question:
                total += question.answer_score
        return total

    def _index(self) -> int:
        self.check_singleton()
        return list(self.survey_id.question_and_page_ids).index(self)

    def _update_time_limit_from_survey(
        self, is_time_limited: bool | None = None, time_limit: int | None = None
    ) -> None:
        write_vals = {}
        if is_time_limited is not None:
            write_vals["is_time_limited"] = is_time_limited
        if time_limit is not None:
            write_vals["time_limit"] = time_limit
        non_time_customized_questions = self.filtered(
            lambda s: not s.is_time_customized
        )
        non_time_customized_questions.write(write_vals)

        customized_questions = self - non_time_customized_questions
        back_to_default_questions = customized_questions.filtered(
            lambda q: (
                q.is_time_limited == q.survey_id.session_speed_rating
                and (
                    q.is_time_limited is False
                    or q.time_limit == q.survey_id.session_speed_rating_time_limit
                )
            )
        )
        back_to_default_questions.is_time_customized = False
