# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.addons.survey.controllers.main import Survey


class RecruitmentSurvey(Survey):

    def _check_validity(self, survey_token, answer_token, ensure_token=True, check_partner=True):
        check_partner = check_partner and not request.env.user.has_group('hr_recruitment.group_hr_recruitment_user')
        return super(RecruitmentSurvey, self)._check_validity(survey_token, answer_token, ensure_token, check_partner)
