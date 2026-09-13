from odoo import fields, models


class SurveyQuestionAnswer(models.Model):
    _inherit = "survey.question.answer"

    generate_lead = fields.Boolean(
        string="Lead creation",
        help="Creates a lead when participants choose this answer",
    )
