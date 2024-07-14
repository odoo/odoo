# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import controllers


def _setup_survey_template(env):
    default_template = env['res.company']._get_default_appraisal_survey_template_id()
    env['res.company'].search([]).write({
        'appraisal_survey_template_id': default_template.id,
    })

    # if hr_recruitment_survey is alrady installed we need to override survey.survey_user_input_rule_survey_user_read
    # because otherwise domain that is set in hr_recruitment_survey is wiped out
    if env['ir.module.module'].search([('name', '=', 'hr_recruitment_survey'), ('state', '=', 'installed')]):
        rule = env.ref("survey.survey_user_input_rule_survey_user_read", raise_if_not_found=False)
        if rule:
            rule.domain_force = [('applicant_id', '=', False), ('survey_id.survey_type', '!=', 'appraisal')]

def uninstall_hook(env):
    xml_ids = [
        'survey.survey_user_input_rule_survey_manager',
        'survey.survey_user_input_rule_survey_user_read',
        'survey.survey_user_input_rule_survey_user_cw',
        'survey.survey_user_input_line_rule_survey_manager',
        'survey.survey_user_input_line_rule_survey_user_read',
        'survey.survey_user_input_line_rule_survey_user_cw'
    ]
    domain = "('survey_id.survey_type', '!=', 'appraisal')"
    for xml_id in xml_ids:
        rule = env.ref(xml_id, raise_if_not_found=False)
        if rule:
            rule.domain_force = rule.domain_force.replace(domain, "(1, '=', 1)")

    action_xml_ids = [
        'survey.action_survey_form',
        'survey.action_survey_question_form',
        'survey.survey_question_answer_action',
        'survey.action_survey_user_input',
        'survey.survey_user_input_line_action'
    ]
    for xml_id in action_xml_ids:
        act_window = env.ref(xml_id, raise_if_not_found=False)
        if act_window and act_window.domain and 'appraisal' in act_window.domain and 'survey_type' in act_window.domain:
            if 'is_page' in act_window.domain:
                act_window.domain = [('is_page', '=', False)]
            else:
                act_window.domain = []
