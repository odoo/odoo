from odoo import api, models, fields


class SurveyQuestion(models.Model):
    _inherit = "survey.question"

    survey_type = fields.Selection(related='survey_id.survey_type', string='Survey Type', readonly=True)
    is_lead_generating = fields.Boolean(
        'Lead generating', default=False, compute="_compute_is_lead_generating",
        help="At least one of its answers can generate leads.")

    @api.depends('question_type', 'suggested_answer_ids', 'suggested_answer_ids.create_lead')
    def _compute_is_lead_generating(self):
        for question in self:
            if question.question_type in ["simple_choice", "multiple_choice", "matrix"]:
                question.is_lead_generating = any(answer.create_lead for answer in question.suggested_answer_ids)
            else:
                question.is_lead_generating = False
