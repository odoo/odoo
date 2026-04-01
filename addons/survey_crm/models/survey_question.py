from odoo import api, models, fields


class SurveyQuestion(models.Model):
    _inherit = 'survey.question'

    survey_type = fields.Selection(related='survey_id.survey_type')
    generate_lead = fields.Boolean(
        'Lead Generating', compute='_compute_generate_lead',
        help='At least one of the question answers can generate leads.')

    @api.depends('question_type', 'suggested_answer_ids')
    def _compute_generate_lead(self):
        for question in self:
            question.generate_lead = question.question_type in ['simple_choice', 'multiple_choice', 'matrix'] and \
                any(answer.generate_lead for answer in question.suggested_answer_ids)
