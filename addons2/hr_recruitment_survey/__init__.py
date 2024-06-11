# -*- coding: utf-8 -*-

from . import models
from . import wizard
from . import controllers


def _correct_survey_rule(env):
    # if hr_appraisal_survey is alrady installed we need to override survey.survey_user_input_rule_survey_user_read
    # because otherwise domain that is set in hr_appraisal_survey is wiped out
    if env['ir.module.module'].search([('name', '=', 'hr_appraisal_survey'), ('state', '=', 'installed')]):
        record = env.ref("survey.survey_user_input_rule_survey_user_read", raise_if_not_found=False)
        if record:
            record.domain_force = [('applicant_id', '=', False), ('survey_id.survey_type', '!=', 'appraisal')]


def uninstall_hook(env):
    rule = env.ref("survey.survey_user_input_rule_survey_user_read", raise_if_not_found=False)
    if rule:
        domain = "('applicant_id', '=', False)"
        rule.domain_force = rule.domain_force.replace(domain, "(1, '=', 1)")
