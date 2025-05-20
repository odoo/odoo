# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.survey.controllers import main


class ApplicantSurvey(main.Survey):
    def _prepare_retry_additional_values(self, answer):
        result = super()._prepare_retry_additional_values(answer)
        if answer.applicant_id:
            result["applicant_id"] = answer.applicant_id.id

        return result

    def _check_validity(
        self,
        survey_sudo,
        answer_sudo,
        answer_token,
        ensure_token=True,
        check_partner=True,
    ):
        validity_code = super()._check_validity(
            survey_sudo, answer_sudo, answer_token, ensure_token, check_partner
        )
        if validity_code is not True:
            return validity_code  # survey is invalid already
        if answer_sudo.state == 'cancelled':
            return "survey_closed"
        return True
