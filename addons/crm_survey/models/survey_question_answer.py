from odoo import fields, models


class SurveyQuestionAnswer(models.Model):
    _inherit = "survey.question.answer"

    create_lead = fields.Boolean('Lead creation', help='A lead will be created if the participant chooses this answer.')
