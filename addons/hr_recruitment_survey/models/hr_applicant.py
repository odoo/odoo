# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Applicant(models.Model):
    _inherit = "hr.applicant"

    survey_id = fields.Many2one('survey.survey', related='job_id.survey_id', string="Survey", readonly=True)
    response_id = fields.Many2one('survey.user_input', "Response", ondelete="set null", oldname="response")

    def action_start_survey(self):
        self.ensure_one()
        # create a response and link it to this applicant
        if not self.response_id:
            response = self.env['survey.user_input'].create({'survey_id': self.survey_id.id, 'partner_id': self.partner_id.id})
            self.response_id = response.id
        else:
            response = self.response_id
        # grab the token of the response and start surveying
        return self.survey_id.with_context(survey_token=response.token).action_start_survey()

    def action_print_survey(self):
        """ If response is available then print this response otherwise print survey form (print template of the survey) """
        self.ensure_one()
        if not self.response_id:
            return self.survey_id.action_print_survey()
        else:
            response = self.response_id
            return self.survey_id.with_context(survey_token=response.token).action_print_survey()
