# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Job(models.Model):
    _inherit = "hr.job"

    survey_id = fields.Many2one(
        'survey.survey', "Interview Form",
        help="Choose an interview form for this job position and you will be able to print/answer this interview from all applicants who apply for this job")

    @api.multi
    def action_print_survey(self):
        return self.survey_id.action_print_survey()
