# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class SurveySurvey(models.Model):
    _inherit = 'survey.survey'

    survey_type = fields.Selection(selection_add=[('recruitment', 'Recruitment')], ondelete={'recruitment': 'set default'})
    hr_job_ids = fields.One2many("hr.job", "survey_id", string="Job Position")

    @api.depends('survey_type')
    @api.depends_context('uid')
    def _compute_allowed_survey_types(self):
        super()._compute_allowed_survey_types()
        if self.env.user.has_group('hr_recruitment.group_hr_recruitment_interviewer') or \
                self.env.user.has_group('survey.group_survey_user'):
            self.allowed_survey_types = (self.allowed_survey_types or []) + ['recruitment']

    @api.depends('hr_job_ids.interviewer_ids', 'hr_job_ids.application_ids.interviewer_ids')
    def _compute_can_access_survey(self):
        return super()._compute_can_access_survey()

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
                hr_recruitment_survey_domain = expression.OR([hr_recruitment_survey_domain, interviewer_domain])  # note: recruitment user inherits from interviewer access rules
        return expression.OR([domain, hr_recruitment_survey_domain])

    @api.model
    def _get_access_survey_type_recruitment(self):
        return [('survey_type', '=', 'recruitment')]

    @api.model
    def _get_access_domain_interviewer(self):
        return expression.OR([
            [('hr_job_ids.interviewer_ids', 'in', self.env.uid)],
            [('hr_job_ids.application_ids.interviewer_ids', 'in', self.env.uid)]])

    def get_formview_id(self, access_uid=None):
        if self.survey_type == 'recruitment':
            access_user = self.env['res.users'].browse(access_uid) if access_uid else self.env.user
            if not access_user.has_group('survey.group_survey_user'):
                if view := self.env.ref('hr_recruitment_survey.survey_survey_view_form', raise_if_not_found=False):
                    return view.id
        return super().get_formview_id(access_uid=access_uid)
