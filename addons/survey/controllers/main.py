# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import werkzeug
from datetime import datetime
from math import ceil

from odoo import fields, http
from odoo.addons.base.models.ir_ui_view import keep_query
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import ustr

_logger = logging.getLogger(__name__)


class Survey(http.Controller):

    def _fetch_from_access_token(self, survey_id, access_token):
        """ Check that given token matches an answer from the given survey_id.
        Returns a sudo-ed browse record of survey in order to avoid access rights
        issues now that access is granted through token. """
        survey_sudo = request.env['survey.survey'].with_context(active_test=False).sudo().browse(survey_id)
        if not access_token:
            answer_sudo = request.env['survey.user_input'].sudo()
        else:
            answer_sudo = request.env['survey.user_input'].sudo().search([
                ('survey_id', '=', survey_sudo.id),
                ('token', '=', access_token)
            ], limit=1)
        return survey_sudo, answer_sudo

    def _check_validity(self, survey_id, access_token, ensure_token=True):
        """ Check survey is open and can be taken. This does not checks for
        security rules, only functional / business rules. It returns a string key
        allowing further manipulation of validity issues

         * survey_wrong: survey does not exist;
         * survey_auth: authentication is required;
         * survey_closed: survey is closed and does not accept input anymore;
         * survey_void: survey is void and should not be taken;
         * token_wrong: given token not recognized;
         * token_required: no token given although it is necessary to access the
           survey;
         * answer_deadline: token linked to an expired answer;

        :param ensure_token: whether user input existence based on given access token
          should be enforced or not, depending on the route requesting a token or
          allowing external world calls;
        """
        survey_sudo, answer_sudo = self._fetch_from_access_token(survey_id, access_token)

        if not survey_sudo.exists():
            return 'survey_wrong'

        if access_token and not answer_sudo:
            return 'token_wrong'

        if not answer_sudo and ensure_token:
            return 'token_required'
        if not answer_sudo and survey_sudo.access_mode == 'token':
            return 'token_required'

        # Public -> no auth required; Token -> token check hereabove
        if survey_sudo.access_mode not in ['public', 'token'] and request.env.user._is_public():
            return 'survey_auth'

        if survey_sudo.is_closed or not survey_sudo.active:
            return 'survey_closed'

        if not survey_sudo.page_ids:
            return 'survey_void'

        # In case of delayed deadline # TDE FIXME
        if answer_sudo and answer_sudo.deadline:
            dt_now = datetime.now()
            if dt_now > answer_sudo.deadline:
                return 'answer_deadline'

        return True

    def _get_access_data(self, survey_id, access_token, ensure_token=True):
        """ Get back data related to survey and user input, given the ID and access
        token provided by the route.

         : param ensure_token: whether user input existence should be enforced or not(see ``_check_validity``)
        """
        survey_sudo, answer_sudo = request.env['survey.survey'].sudo(), request.env['survey.user_input'].sudo()
        has_survey_access, can_answer = False, False

        validity_code = self._check_validity(survey_id, access_token, ensure_token=ensure_token)
        if validity_code != 'survey_wrong':
            survey_sudo, answer_sudo = self._fetch_from_access_token(survey_id, access_token)
            try:
                survey_user = survey_sudo.sudo(request.env.user)
                survey_user.check_access_rights(self, 'read', raise_exception=True)
                survey_user.check_access_rule(self, 'read')
            except:
                pass
            else:
                has_survey_access = True
            can_answer = bool(answer_sudo)
            if not can_answer:
                can_answer = survey_sudo.access_mode == 'public'

        return {
            'survey_sudo': survey_sudo,
            'answer_sudo': answer_sudo,
            'has_survey_access': has_survey_access,
            'can_answer': can_answer,
            'validity_code': validity_code,
        }

    def _redirect_with_error(self, access_data, error_key):
        survey_sudo = access_data['survey_sudo']
        answer_sudo = access_data['answer_sudo']

        if error_key == 'survey_void' and access_data['can_answer']:
            return request.render("survey.survey_void", {'survey': survey_sudo})
        elif error_key == 'survey_closed' and access_data['can_answer']:
            return request.render("survey.survey_expired", {'survey': survey_sudo})
        elif error_key == 'survey_auth' and answer_sudo.token:
            return request.render("survey.auth_required", {'survey': survey_sudo, 'token': answer_sudo.token})
        elif error_key == 'answer_deadline' and answer_sudo.token:
            return request.render("survey.survey_expired", {'survey': survey_sudo})

        return werkzeug.utils.redirect("/")

    @http.route('/survey/test/<int:survey_id>', type='http', auth='user', website=True)
    def survey_test(self, survey_id, token=None, **kwargs):
        """ Test mode for surveys: create a test answer, only for managers or officers
        testing their surveys """
        survey_sudo = request.env['survey.survey'].sudo().browse(survey_id)
        try:
            answer_sudo = survey_sudo._create_answer(user=request.env.user, test_entry=True)
        except:
            return werkzeug.utils.redirect('/')
        return request.redirect('/survey/start/%s?%s' % (survey_sudo.id, keep_query('*', token=answer_sudo.token)))

    @http.route('/survey/start/<int:survey_id>', type='http', auth='public', website=True)
    def survey_start(self, survey_id, token=None, email=False, **post):
        """ Start a survey by providing a token linked to an answer or generate
        a new token if access is allowed """
        access_data = self._get_access_data(survey_id, token, ensure_token=False)
        if access_data['validity_code'] is not True:
            return self._redirect_with_error(access_data, access_data['validity_code'])

        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']
        if not answer_sudo:
            try:
                answer_sudo = survey_sudo._create_answer(user=request.env.user, email=email)
            except UserError:
                answer_sudo = False

        if not answer_sudo:
            try:
                survey_sudo.sudo(request.env.user).check_access_rights('read')
                survey_sudo.sudo(request.env.user).check_access_rule('read')
            except:
                return werkzeug.utils.redirect("/")
            else:
                return request.render("survey.403", {'survey': survey_sudo})

        # Select the right page
        if answer_sudo.state == 'new':  # Intro page
            data = {'survey': survey_sudo, 'page': None, 'token': answer_sudo.token, 'test_entry': answer_sudo.test_entry}
            return request.render('survey.survey_init', data)
        else:
            return request.redirect('/survey/fill/%s/%s' % (survey_sudo.id, answer_sudo.token))

    @http.route('/survey/fill/<int:survey_id>/<string:token>', type='http', auth='public', website=True)
    def survey_display_page(self, survey_id, token, prev=None, **post):
        access_data = self._get_access_data(survey_id, token, ensure_token=True)
        if access_data['validity_code'] is not True:
            return self._redirect_with_error(access_data, access_data['validity_code'])

        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']

        # Select the right page
        if answer_sudo.state == 'new':  # First page
            page, page_nr, last = survey_sudo.next_page(answer_sudo, 0, go_back=False)
            data = {'survey': survey_sudo, 'page': page, 'page_nr': page_nr, 'answer': answer_sudo}
            if last:
                data.update({'last': True})
            return request.render('survey.survey', data)
        elif answer_sudo.state == 'done':  # Display success message
            return request.render('survey.sfinished', {'survey': survey_sudo,
                                                       'token': token,
                                                       'user_input': answer_sudo})
        elif answer_sudo.state == 'skip':
            flag = (True if prev and prev == 'prev' else False)
            page, page_nr, last = survey_sudo.next_page(answer_sudo, answer_sudo.last_displayed_page_id.id, go_back=flag)

            #special case if you click "previous" from the last page, then leave the survey, then reopen it from the URL, avoid crash
            if not page:
                page, page_nr, last = survey_sudo.next_page(answer_sudo, answer_sudo.last_displayed_page_id.id, go_back=True)

            data = {'survey': survey_sudo, 'page': page, 'page_nr': page_nr, 'answer': answer_sudo}
            if last:
                data.update({'last': True})
            return request.render('survey.survey', data)
        else:
            return request.render("survey.403", {'survey': survey_sudo})

    @http.route('/survey/validate/<int:survey_id>/<string:token>', type='json', auth='public', website=True)
    def survey_validate(self, survey_id, token, **post):
        access_data = self._get_access_data(survey_id, token, ensure_token=True)
        if access_data['validity_code'] is not True:
            return {
                'error': access_data['validity_code'],
                'fields': {},
            }

        page_id = int(post['page_id'])
        questions = request.env['survey.question'].sudo().search([
            ('survey_id', '=', survey_id),
            ('page_id', '=', page_id)
        ])

        errors = {}
        for question in questions:
            answer_tag = "%s_%s_%s" % (survey_id, page_id, question.id)
            errors.update(question.validate_question(post, answer_tag))

        if errors:
            return {
                'error': 'validation',
                'fields': errors,
            }
        return True

    @http.route('/survey/submit/<int:survey_id>/<string:token>', type='http', methods=['POST'], auth='public', website=True)
    def survey_submit(self, survey_id, token, **post):
        # print('-------------------------')
        # print(survey_id, token)
        # print(post)
        # print('-------------------------')
        access_data = self._get_access_data(survey_id, token, ensure_token=True)
        if access_data['validity_code'] is not True:
            return {}

        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']

        page_id = int(post['page_id'])
        questions = request.env['survey.question'].sudo().search([
            ('survey_id', '=', survey_id),
            ('page_id', '=', page_id)
        ])
        for question in questions:
            answer_tag = "%s_%s_%s" % (survey_id, page_id, question.id)
            request.env['survey.user_input_line'].sudo().save_lines(answer_sudo.id, question, post, answer_tag)

        go_back = post.get('prev') == 'prev'
        next_page, _, last = request.env['survey.survey'].next_page(answer_sudo, page_id, go_back=go_back)
        vals = {'last_displayed_page_id': page_id}
        if next_page is None and not go_back:
            vals.update({'state': 'done'})
        else:
            vals.update({'state': 'skip'})
        answer_sudo.write(vals)
        url = '/survey/fill/%s/%s' % (survey_sudo.id, token)
        if go_back:
            url += '?prev=prev'
        return request.redirect(url)

    @http.route('/survey/print/<int:survey_id>', type='http', auth='public', website=True)
    def survey_print(self, survey_id, token=None, **post):
        '''Display an survey in printable view; if <token> is set, it will
        grab the answers of the user_input_id that has <token>.'''
        access_data = self._get_access_data(survey_id, token, ensure_token=False)
        if access_data['validity_code'] is not True and (
            not access_data['has_survey_access'] or access_data['validity_code'] not in ['token_required', 'survey_closed', 'survey_void']):
            return self._redirect_with_error(access_data, access_data['validity_code'])

        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']

        return request.render('survey.survey_print', {
            'survey': survey_sudo,
            'answer': answer_sudo
        })

    @http.route('/survey/results/<model("survey.survey"):survey>', type='http', auth='user', website=True)
    def survey_report(self, survey, token=None, **post):
        '''Display survey Results & Statistics for given survey.'''
        result_template = 'survey.result'
        current_filters = []
        filter_display_data = []
        filter_finish = False

        if not survey.user_input_ids or not [input_id.id for input_id in survey.user_input_ids if input_id.state != 'new']:
            result_template = 'survey.no_result'
        if 'finished' in post:
            post.pop('finished')
            filter_finish = True
        if post or filter_finish:
            filter_data = self._get_filter_data(post)
            current_filters = survey.filter_input_ids(filter_data, filter_finish)
            filter_display_data = survey.get_filter_display_data(filter_data)
        return request.render(result_template,
                                      {'survey': survey,
                                       'survey_dict': self._prepare_result_dict(survey, current_filters),
                                       'page_range': self.page_range,
                                       'current_filters': current_filters,
                                       'filter_display_data': filter_display_data,
                                       'filter_finish': filter_finish
                                       })
        # Quick retroengineering of what is injected into the template for now:
        # (TODO: flatten and simplify this)
        #
        #     survey: a browse record of the survey
        #     survey_dict: very messy dict containing all the info to display answers
        #         {'page_ids': [
        #
        #             ...
        #
        #                 {'page': browse record of the page,
        #                  'question_ids': [
        #
        #                     ...
        #
        #                     {'graph_data': data to be displayed on the graph
        #                      'input_summary': number of answered, skipped...
        #                      'prepare_result': {
        #                                         answers displayed in the tables
        #                                         }
        #                      'question': browse record of the question_ids
        #                     }
        #
        #                     ...
        #
        #                     ]
        #                 }
        #
        #             ...
        #
        #             ]
        #         }
        #
        #     page_range: pager helper function
        #     current_filters: a list of ids
        #     filter_display_data: [{'labels': ['a', 'b'], question_text} ...  ]
        #     filter_finish: boolean => only finished surveys or not
        #

    def _prepare_result_dict(self, survey, current_filters=None):
        """Returns dictionary having values for rendering template"""
        current_filters = current_filters if current_filters else []
        Survey = request.env['survey.survey']
        result = {'page_ids': []}
        for page in survey.page_ids:
            page_dict = {'page': page, 'question_ids': []}
            for question in page.question_ids:
                question_dict = {
                    'question': question,
                    'input_summary': Survey.get_input_summary(question, current_filters),
                    'prepare_result': Survey.prepare_result(question, current_filters),
                    'graph_data': self._get_graph_data(question, current_filters),
                }

                page_dict['question_ids'].append(question_dict)
            result['page_ids'].append(page_dict)
        return result

    def _get_filter_data(self, post):
        """Returns data used for filtering the result"""
        filters = []
        for ids in post:
            #if user add some random data in query URI, ignore it
            try:
                row_id, answer_id = ids.split(',')
                filters.append({'row_id': int(row_id), 'answer_id': int(answer_id)})
            except:
                return filters
        return filters

    def page_range(self, total_record, limit):
        '''Returns number of pages required for pagination'''
        total = ceil(total_record / float(limit))
        return range(1, int(total + 1))

    def _get_graph_data(self, question, current_filters=None):
        '''Returns formatted data required by graph library on basis of filter'''
        # TODO refactor this terrible method and merge it with _prepare_result_dict
        current_filters = current_filters if current_filters else []
        Survey = request.env['survey.survey']
        result = []
        if question.question_type == 'multiple_choice':
            result.append({'key': ustr(question.question),
                           'values': Survey.prepare_result(question, current_filters)['answers']
                           })
        if question.question_type == 'simple_choice':
            result = Survey.prepare_result(question, current_filters)['answers']
        if question.question_type == 'matrix':
            data = Survey.prepare_result(question, current_filters)
            for answer in data['answers']:
                values = []
                for row in data['rows']:
                    values.append({'text': data['rows'].get(row), 'count': data['result'].get((row, answer))})
                result.append({'key': data['answers'].get(answer), 'values': values})
        return json.dumps(result)
