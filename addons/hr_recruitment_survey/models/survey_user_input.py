# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.osv import expression


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    applicant_id = fields.Many2one('hr.applicant', string='Applicant')

    def _mark_done(self):
        odoobot = self.env.ref('base.partner_root')
        for user_input in self:
            if user_input.applicant_id:
                body = _('The applicant "%s" has finished the survey.', user_input.applicant_id.partner_name)
                user_input.applicant_id.message_post(body=body, author_id=odoobot.id)
        return super()._mark_done()

    @api.depends('applicant_id.interviewer_ids', 'applicant_id.job_id.interviewer_ids')
    def _compute_can_access_survey_user_input(self):
        return super()._compute_can_access_survey_user_input()

    def _get_access_domain(self):
        domain = super()._get_access_domain()
        hr_recruitment_survey_domain = expression.FALSE_DOMAIN

        if self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager'):
            hr_recruitment_survey_domain = self._get_access_survey_type_recruitment()
        else:
            if self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
                hr_recruitment_survey_domain = expression.AND([
                    self._get_access_survey_type_recruitment(),
                    self._get_access_domain_restricted_user_ids()])
            if self.env.user.has_group('hr_recruitment.group_hr_recruitment_interviewer'):
                interviewer_domain = expression.AND([
                    self._get_access_survey_type_recruitment(),
                    self._get_access_domain_interviewer()
                ])
                hr_recruitment_survey_domain = expression.OR([hr_recruitment_survey_domain, interviewer_domain])
        return expression.OR([domain, hr_recruitment_survey_domain])

    @api.model
    def _get_access_survey_type_recruitment(self):
        return [('survey_id.survey_type', '=', 'recruitment')]

    @api.model
    def _get_access_domain_interviewer(self):
        return expression.OR([
            [('applicant_id.interviewer_ids', 'in', self.env.uid)],
            [('applicant_id.job_id.interviewer_ids', 'in', self.env.uid)]])
