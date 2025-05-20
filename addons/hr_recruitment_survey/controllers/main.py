# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.survey.controllers import main
from odoo import http
from odoo.http import request


class ApplicantSurvey(main.Survey):
    def _prepare_retry_additional_values(self, answer):
        result = super()._prepare_retry_additional_values(answer)
        if answer.applicant_id:
            result["applicant_id"] = answer.applicant_id.id

        return result

    @http.route()
    def survey_start(self, survey_token, answer_token=None, email=False, **post):
        if answer_token:
            access_data = self._get_access_data(survey_token, answer_token, ensure_token=False)
            answer_sudo = access_data['answer_sudo']
            applicant_sudo = request.env['hr.applicant'].sudo().with_context(active_test=False).search([('partner_id', '=', answer_sudo.partner_id.id)])
            if applicant_sudo and (not applicant_sudo.active or applicant_sudo.stage_id.hired_stage):
                return request.render('hr_recruitment_survey.survey_applicant_link_expired')
        return super().survey_start(survey_token, answer_token, email, **post)
