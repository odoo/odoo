from odoo import fields, models


class SurveySurvey(models.Model):
    _inherit = "survey.survey"

    slide_ids = fields.One2many(
        comodel_name="slide.slide",
        inverse_name="survey_id",
        string="Slides",
        help="The slides this survey is linked to through the eLearning application",
    )
