# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SlideQuestion(models.Model):
    _name = "slide.question"
    _rec_name = "question"
    _description = "Content Quiz Question"

    sequence = fields.Integer("Sequence", default=10)
    question = fields.Char("Question Name", required=True, translate=True)
    slide_id = fields.Many2one('slide.slide', string="Content", required=True)
    answer_ids = fields.One2many('slide.answer', 'question_id', string="Answer")
    # statistics
    attempts_count = fields.Integer(compute='_compute_statistics', groups='website.group_website_publisher')
    attempts_avg = fields.Float(compute="_compute_statistics", digits=(6, 2), groups='website.group_website_publisher')
    done_count = fields.Integer(compute="_compute_statistics", groups='website.group_website_publisher')

    @api.constrains('answer_ids')
    def _check_only_one_good_answer(self):
        for question in self:
            good_answer_count = 0
            for answer in question.answer_ids:
                if answer.is_correct:
                    good_answer_count += 1
                    if good_answer_count > 1:
                        raise ValidationError(_('Question "%s" can only have one good answer') % question.question)

    @api.constrains('answer_ids')
    def _check_correct_answer(self):
        for question in self:
            if not any([answer.is_correct for answer in question.answer_ids]):
                raise ValidationError(_('Question "%s" must at least have one good answer') % question.question)

    @api.constrains('answer_ids')
    def _check_at_least_2_answers(self):
        for question in self:
            if len(question.answer_ids) < 2:
                raise ValidationError(_('Question "%s" has no valid answer, please set one') % question.question)

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


class SlideAnswer(models.Model):
    _name = "slide.answer"
    _rec_name = "text_value"
    _description = "Answer for a slide question"
    _order = 'question_id, id'

    question_id = fields.Many2one('slide.question', string="Question", required=True)
    text_value = fields.Char("Answer", required=True, translate=True)
    is_correct = fields.Boolean("Is correct answer")
