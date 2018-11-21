# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SlideQuestion(models.Model):
    _name = "slide.question"
    _rec_name = "question"
    _description = """
        Question for a slide. A slide can have multiple questions and each question
        must have at least 2 possible answers and only one good answer.
        """

    sequence = fields.Integer("Sequence", default=10)
    question = fields.Char("Question Name", required=True)
    slide_id = fields.Many2one('slide.slide', string="Slide")
    answer_ids = fields.One2many('slide.answer', 'question_id', string="Answer")

    @api.constrains('answer_ids')
    def _check_only_one_good_answer(self):
        for question in self:
            good_answer_count = 0
            for answer in question.answer_ids:
                if answer.is_correct:
                    good_answer_count += 1
                    if good_answer_count > 1:
                        raise ValidationError(_('A question can only have one good answer'))

    @api.constrains('answer_ids')
    def _check_correct_answer(self):
        for question in self:
            if not any([answer.is_correct for answer in question.answer_ids]):
                raise ValidationError(_("A question must at least have one good answer"))

    @api.constrains('answer_ids')
    def _check_at_least_2_answers(self):
        for question in self:
            if len(question.answer_ids) < 2:
                raise ValidationError(_("A question must at least have two possible answers"))


class SlideAnswer(models.Model):
    _name = "slide.answer"
    _rec_name = "text_value"
    _description = """Answer for a slide question"""

    question_id = fields.Many2one('slide.question', string="Question")
    text_value = fields.Char("Answer", required=True,)
    is_correct = fields.Boolean("Is correct answer", default=False)
