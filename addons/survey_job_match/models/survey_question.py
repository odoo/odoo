from odoo import fields, models


class SurveyQuestionAnswer(models.Model):
    _inherit = 'survey.question.answer'

    match_weight_ids = fields.One2many(
        'job.match.answer.weight', 'answer_id', string='Job Match Weights')
