from odoo import api, models, fields


class SurveyQuestion(models.Model):
    _inherit = "survey.question"

    survey_type = fields.Selection(related='survey_id.survey_type', string='Survey Type', readonly=True)
    is_lead_generating = fields.Boolean('Lead generating', default=False, compute="_compute_is_lead_generating",
                                         help="At least one of its answers can generate leads.")

    @api.depends('question_ids')
    def _compute_is_lead_generating(self):
        """
        Compute the boolean to know if (at least) an answer can trigger a lead.
        """
        for question in self:
            question.is_lead_generating = False
            if question.question_type in ["simple_choice", "multiple_choice", "matrix"]:
                for answer in question.suggested_answer_ids:
                    if answer.create_lead:
                        question.is_lead_generating = True
                        break
