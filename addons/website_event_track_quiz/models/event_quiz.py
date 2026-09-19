from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class EventQuiz(models.Model):
    _name = "event.quiz"
    _description = "Quiz"

    name = fields.Char(
        translate=True,
        required=True,
    )
    question_ids = fields.One2many(
        comodel_name="event.quiz.question",
        inverse_name="quiz_id",
        string="Questions",
    )
    event_track_id = fields.Many2one(
        comodel_name="event.track",
        index="btree_not_null",
        readonly=True,
    )
    event_id = fields.Many2one(
        comodel_name="event.event",
        related="event_track_id.event_id",
        readonly=True,
    )
    repeatable = fields.Boolean(
        string="Unlimited Tries",
        help="Let attendees reset the quiz and try again.",
    )


class EventQuizQuestion(models.Model):
    _name = "event.quiz.question"
    _description = "Content Quiz Question"
    _order = "quiz_id, sequence, id"

    name = fields.Char(
        string="Question",
        translate=True,
        required=True,
    )
    sequence = fields.Integer()
    quiz_id = fields.Many2one(
        comodel_name="event.quiz",
        index=True,
        required=True,
        ondelete="cascade",
    )
    correct_answer_id = fields.One2many(
        comodel_name="event.quiz.answer",
        compute="_compute_correct_answer_id",
    )
    awarded_points = fields.Integer(
        string="Number of Points",
        compute="_compute_awarded_points",
    )
    answer_ids = fields.One2many(
        comodel_name="event.quiz.answer",
        inverse_name="question_id",
    )

    @api.depends("answer_ids.awarded_points")
    def _compute_awarded_points(self):
        for question in self:
            question.awarded_points = sum(question.answer_ids.mapped("awarded_points"))

    @api.depends("answer_ids.is_correct")
    def _compute_correct_answer_id(self):
        for question in self:
            question.correct_answer_id = question.answer_ids.filtered(
                lambda e: e.is_correct
            )

    @api.constrains("answer_ids")
    def _check_answers_integrity(self):
        for question in self:
            if len(question.correct_answer_id) != 1:
                _debug.logic(
                    "quiz_question_refused",
                    reason="not_exactly_one_correct_answer",
                    question=question.id,
                )
                raise ValidationError(
                    _(
                        'Question "%s" must have 1 correct answer to be valid.',
                        question.name,
                    )
                )
            if len(question.answer_ids) < 2:
                _debug.logic(
                    "quiz_question_refused",
                    reason="too_few_answers",
                    question=question.id,
                )
                raise ValidationError(
                    _(
                        'Question "%s" must have 1 correct answer and at least 1 incorrect answer to be valid.',
                        question.name,
                    )
                )


class EventQuizAnswer(models.Model):
    _name = "event.quiz.answer"
    _rec_name = "text_value"
    _description = "Question's Answer"
    _order = "question_id, sequence, id"

    sequence = fields.Integer()
    question_id = fields.Many2one(
        comodel_name="event.quiz.question",
        index=True,
        required=True,
        ondelete="cascade",
    )
    text_value = fields.Char(
        string="Answer",
        translate=True,
        required=True,
    )
    is_correct = fields.Boolean(
        string="Correct",
        default=False,
    )
    comment = fields.Text(
        string="Extra Comment",
        translate=True,
        help="""This comment will be displayed to the user if they select this answer, after submitting the quiz.
                It is used as a small informational text helping to understand why this answer is correct / incorrect.""",
    )
    awarded_points = fields.Integer(
        string="Points",
        default=0,
    )
