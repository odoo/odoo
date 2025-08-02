from odoo import fields, models


class SurveyQuestionAnswer(models.Model):
    _inherit = "survey.question.answer"

    is_create_lead = fields.Boolean('Lead creation', help='A lead will be created if the participant chooses this answer.')
