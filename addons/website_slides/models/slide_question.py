# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SlideQuestion(models.Model):
    _name = 'slide.question'
    _rec_name = "question"
    _description = "Content Quiz Question"
    _order = "sequence"

    sequence = fields.Integer("Sequence")
    question = fields.Char("Question Name", required=True, translate=True)
    slide_id = fields.Many2one('slide.slide', string="Content", required=True, index=True, ondelete='cascade')
    answer_ids = fields.One2many('slide.answer', 'question_id', string="Answer", copy=True)
    answers_validation_error = fields.Char("Error on Answers", compute='_compute_answers_validation_error')
    # statistics
    attempts_count = fields.Integer(compute='_compute_statistics', groups='website_slides.group_website_slides_officer')
    attempts_avg = fields.Float(compute="_compute_statistics", digits=(6, 2), groups='website_slides.group_website_slides_officer')
    done_count = fields.Integer(compute="_compute_statistics", groups='website_slides.group_website_slides_officer')

    @api.constrains('answer_ids')
    def _check_answers_integrity(self):
        questions_to_fix = [
            f'- {question.slide_id.name}: {question.question}'
            for question in self
            if question.answers_validation_error
        ]
        if questions_to_fix:
            raise ValidationError(_(
                'All questions must have at least one correct answer and one incorrect answer: \n%s\n',
                '\n'.join(questions_to_fix)))

    @api.depends('slide_id')
    def _compute_statistics(self):
        slide_partners = self.env['slide.slide.partner'].sudo().search([('slide_id', 'in', self.slide_id.ids)])
        slide_stats = dict((s.slide_id.id, dict({'attempts_count': 0, 'attempts_unique': 0, 'done_count': 0})) for s in slide_partners)

        for slide_partner in slide_partners:
            slide_stats[slide_partner.slide_id.id]['attempts_count'] += slide_partner.quiz_attempts_count
            slide_stats[slide_partner.slide_id.id]['attempts_unique'] += 1
            if slide_partner.completed:
                slide_stats[slide_partner.slide_id.id]['done_count'] += 1

        for question in self:
            stats = slide_stats.get(question.slide_id.id)
            question.attempts_count = stats.get('attempts_count', 0) if stats else 0
            question.attempts_avg = stats.get('attempts_count', 0) / stats.get('attempts_unique', 1) if stats else 0
            question.done_count = stats.get('done_count', 0) if stats else 0

    @api.depends('answer_ids', 'answer_ids.is_correct')
    def _compute_answers_validation_error(self):
        for question in self:
            correct = question.answer_ids.filtered('is_correct')
            question.answers_validation_error = _(
                'This question must have at least one correct answer and one incorrect answer.'
            ) if not correct or correct == question.answer_ids else ''


class SlideAnswer(models.Model):
    _name = 'slide.answer'
    _rec_name = "text_value"
    _description = "Slide Question's Answer"
    _order = 'question_id, sequence, id'

    sequence = fields.Integer("Sequence")
    question_id = fields.Many2one('slide.question', string="Question", required=True, index=True, ondelete='cascade')
    text_value = fields.Char("Answer", required=True, translate=True)
    is_correct = fields.Boolean("Is correct answer")
    comment = fields.Text("Comment", translate=True, help='This comment will be displayed to the user if they select this answer')
