# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EventQuiz(models.Model):
    _name = 'event.quiz'
    _description = "Quiz"

    name = fields.Char('Name', required=True, translate=True)
    question_ids = fields.One2many('event.quiz.question', 'quiz_id', string="Questions")
    event_track_id = fields.Many2one('event.track', readonly=True, index='btree_not_null')
    event_id = fields.Many2one(
        'event.event', related='event_track_id.event_id',
        readonly=True, store=True)
    repeatable = fields.Boolean('Unlimited Tries',
        help='Let attendees reset the quiz and try again.')


class EventQuizQuestion(models.Model):
    _name = 'event.quiz.question'
    _description = "Content Quiz Question"
    _order = "quiz_id, sequence, id"

    name = fields.Char("Question", required=True, translate=True)
    sequence = fields.Integer("Sequence")
    quiz_id = fields.Many2one("event.quiz", "Quiz", required=True, index=True, ondelete='cascade')
    correct_answer_id = fields.One2many('event.quiz.answer', compute='_compute_correct_answer_id')
    awarded_points = fields.Integer("Number of Points", compute='_compute_awarded_points')
    answer_ids = fields.One2many('event.quiz.answer', 'question_id', string="Answer")

    @api.depends('answer_ids.awarded_points')
    def _compute_awarded_points(self):
        for question in self:
            question.awarded_points = sum(question.answer_ids.mapped('awarded_points'))

    @api.depends('answer_ids.is_correct')
    def _compute_correct_answer_id(self):
        for question in self:
            question.correct_answer_id = question.answer_ids.filtered(lambda e: e.is_correct)

    @api.constrains('answer_ids')
    def _check_answers_integrity(self):
        for question in self:
            if len(question.correct_answer_id) != 1:
                raise ValidationError(_('Question "%s" must have 1 correct answer to be valid.', question.name))
            if len(question.answer_ids) < 2:
                raise ValidationError(_('Question "%s" must have 1 correct answer and at least 1 incorrect answer to be valid.', question.name))


class EventQuizAnswer(models.Model):
    _name = 'event.quiz.answer'
    _rec_name = "text_value"
    _description = "Question's Answer"
    _order = 'question_id, sequence, id'

    sequence = fields.Integer("Sequence")
    question_id = fields.Many2one('event.quiz.question', string="Question", required=True, index=True, ondelete='cascade')
    text_value = fields.Char("Answer", required=True, translate=True)
    is_correct = fields.Boolean('Correct', default=False)
    comment = fields.Text(
        'Extra Comment', translate=True,
        help='''This comment will be displayed to the user if they select this answer, after submitting the quiz.
                It is used as a small informational text helping to understand why this answer is correct / incorrect.''')
    awarded_points = fields.Integer('Points', default=0)
