# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Quiz(models.Model):
    _name = "event.quiz"
    _description = "Quiz"

    name = fields.Char('name', required=True, translate=True)
    question_ids = fields.One2many('event.quiz.question', 'quiz_id', string="Questions")

class QuizQuestion(models.Model):
    _name = "event.quiz.question"
    _description = "Content Quiz Question"
    _order = "sequence"

    sequence = fields.Integer("Sequence")
    name = fields.Char("Question Name", required=True, translate=True)
    quiz_id = fields.Many2one("event.quiz", "Quiz", required=True, ondelete='cascade')
    awarded_points = fields.Integer("Number of points", default=1)

    answer_ids = fields.One2many('event.quiz.question.answer', 'question_id', string="Answer")

    @api.constrains('answer_ids')
    def _check_answers_integrity(self):
        for question in self:
            if len(question.answer_ids.filtered(lambda answer: answer.is_correct)) != 1:
                raise ValidationError(_('Question "%s" must have 1 correct answer') % question.question)
            if len(question.answer_ids) < 2:
                raise ValidationError(_('Question "%s" must have 1 correct answer and at least 1 invalid answer') % question.question)

class QuizAnswer(models.Model):
    _name = "event.quiz.question.answer"
    _rec_name = "text_value"
    _description = "Question's Answer"
    _order = 'question_id, sequence'

    sequence = fields.Integer("Sequence")
    question_id = fields.Many2one('event.quiz.question', string="Question", required=True, ondelete='cascade')
    text_value = fields.Char("Answer", required=True, translate=True)
    is_correct = fields.Boolean("Is correct answer")
    comment = fields.Text("Comment", translate=True, help='This comment will be displayed to the user if he selects this answer')
    awarded_points = fields.Integer('Number of points', compute='_compute_awarded_points')

    @api.depends('question_id.awarded_points')
    def _compute_awarded_points(self):
        for answer in self:
            answer.awarded_points = answer.question_id.awarded_points if answer.is_correct else 0
