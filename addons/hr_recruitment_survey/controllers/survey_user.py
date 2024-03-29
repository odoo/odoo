# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.survey.controllers import main


class ApplicantSurvey(main.Survey):
    def _prepare_retry_additional_values(self, answer):
        result = super(Survey, self)._prepare_retry_additional_values(answer)
        if answer.applicant_id:
            result["applicant_id"] = answer.applicant_id.id

        return result
