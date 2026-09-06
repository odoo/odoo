from odoo import fields, models


class SurveyQuestionAnswer(models.Model):
    _inherit = 'survey.question.answer'

    match_weight_ids = fields.One2many(
        'job.match.answer.weight', 'answer_id', string='Job Match Weights')
    job_match_result_message = fields.Html(
        'Job Match Result Message', translate=True,
        help="If a participant picks this answer, this message is shown on the result "
             "page instead of a job match. Use it for a dedicated final page, e.g. to "
             "redirect student-job applicants to internships.")
