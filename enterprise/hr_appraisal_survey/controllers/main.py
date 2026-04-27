# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.survey.controllers.main import Survey
from odoo import http
from odoo.exceptions import AccessDenied
from odoo.http import request
from odoo.osv import expression


class AppraisalSurvey(Survey):

    def _check_validity(self, survey_token, answer_token, ensure_token=True, check_partner=True):
        survey_sudo, answer_sudo = self._fetch_from_access_token(survey_token, answer_token)
        validity_code = super()._check_validity(survey_token, answer_token, ensure_token, check_partner)

        if validity_code == 'answer_wrong_user' and survey_sudo.survey_type == 'appraisal' and answer_sudo and check_partner:
            user_employees = request.env['hr.employee'].search([('user_id', '=', request.env.user.id)])
            partners = user_employees.work_contact_id | request.env.user.partner_id
            if not request.env.user._is_public() and answer_sudo.partner_id in partners:
                return True
        return validity_code

    def _get_access_data(self, survey_token, answer_token, ensure_token=True, check_partner=True):
        survey_sudo, answer_sudo = self._fetch_from_access_token(survey_token, answer_token)
        access_data = super()._get_access_data(survey_token, answer_token, ensure_token, check_partner)

        if survey_sudo and answer_sudo and survey_sudo.survey_type == 'appraisal' and access_data.get('validity_code', False) == 'answer_deadline':
            appraisal = answer_sudo.appraisal_id
            user = request.env.user
            if user in appraisal.manager_ids.mapped('user_id') or user.has_group('hr_appraisal.group_hr_appraisal_user'):
                # If the deadline is reached, Appraisal Manager should be able to consult answers
                access_data['can_answer'] = False
                access_data['validity_code'] = True
        return access_data

    def _get_results_page_user_input_domain(self, survey, **post):
        user_input_domain = super()._get_results_page_user_input_domain(survey, **post)
        if not post.get('appraisal_id'):
            return user_input_domain
        appraisal = request.env['hr.appraisal'].sudo().browse(int(post.get('appraisal_id')))
        user = request.env.user
        if user in appraisal.manager_ids.mapped('user_id') or user.has_group('hr_appraisal.group_hr_appraisal_user'):
            return expression.AND([[('appraisal_id', '=', appraisal.id)], user_input_domain])
        if user in appraisal.employee_feedback_ids.mapped('user_id'):
            return expression.AND([[
                ('appraisal_id', '=', appraisal.id),
                ('partner_id', '=', user.partner_id.id)
            ], user_input_domain])
        raise AccessDenied()

    @http.route('/appraisal/<int:appraisal_id>/results', type='http', auth='user', website=True)
    def appraisal_survey_results(self, appraisal_id, **post):
        """ Display survey Results & Statistics for given appraisal.
        """
        # check access rigths using token, get back survey if granted
        appraisal = request.env['hr.appraisal'].sudo().browse(int(appraisal_id))
        if appraisal.employee_id.user_id == request.env.user:
            return request.render(
                'http_routing.http_error',
                {'status_code': 'Oops',
                 'status_message': "Sorry, you can't access to this survey concerning your appraisal..."})
        user = request.env.user
        survey_id = post.get('survey_id', False)
        survey_sudo = request.env['survey.survey']
        if user.has_group('hr_appraisal.group_hr_appraisal_user') or user.has_group('base.group_system') \
                or user in appraisal.manager_ids.mapped('user_id'):
            domain = [('appraisal_id', '=', appraisal.id)]
            if survey_id:
                domain = expression.AND([[('survey_id', '=', int(survey_id))], domain])
            survey_sudo = request.env['survey.user_input'].sudo().search(domain, limit=1).survey_id
        if user in appraisal.employee_feedback_ids.mapped('user_id') and not survey_id:
            answer = request.env['survey.user_input'].sudo().search([
                ('appraisal_id', '=', appraisal.id),
                ('partner_id', '=', request.env.user.partner_id.id),
            ], limit=1)
            if answer:
                survey_sudo = answer.survey_id
        if not survey_sudo:
            raise AccessDenied()

        post['appraisal_id'] = appraisal_id
        user_input_lines_sudo, search_filters = self._extract_filters_data(survey_sudo, post)
        survey_data = survey_sudo._prepare_statistics(user_input_lines_sudo)
        question_and_page_data = survey_sudo.question_and_page_ids._prepare_statistics(user_input_lines_sudo)

        answers = request.env['survey.user_input'].sudo().search([
                ('appraisal_id', '=', appraisal.id),
                ('survey_id', '=', survey_sudo.id),
                ('state', '=', 'done')])

        requestors = answers.mapped('create_uid.partner_id')

        template_values = {
            'survey': survey_sudo,
            'answers': answers,
            'question_and_page_data': question_and_page_data,
            'survey_data': survey_data,
            'search_filters': search_filters,
            'search_finished': 'true',  # always finished
            'appraisal_id': appraisal_id,
            'appraisal_date': appraisal.date_close,
            'employee_name': appraisal.employee_id.name,
            'requestors': requestors,
        }
        return request.render('survey.survey_page_statistics', template_values)
