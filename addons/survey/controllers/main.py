# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import werkzeug

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import fields, http, _
from odoo.addons.base.models.ir_ui_view import keep_query
from odoo.exceptions import UserError
from odoo.http import request, content_disposition
from odoo.osv import expression
from odoo.tools import format_datetime, format_date

from odoo.addons.web.controllers.main import Binary

_logger = logging.getLogger(__name__)


class Survey(http.Controller):

    # ------------------------------------------------------------
    # ACCESS
    # ------------------------------------------------------------

    def _fetch_from_access_token(self, survey_token, answer_token):
        """ Check that given token matches an answer from the given survey_id.
        Returns a sudo-ed browse record of survey in order to avoid access rights
        issues now that access is granted through token. """
        survey_sudo = request.env['survey.survey'].with_context(active_test=False).sudo().search([('access_token', '=', survey_token)])
        if not answer_token:
            answer_sudo = request.env['survey.user_input'].sudo()
        else:
            answer_sudo = request.env['survey.user_input'].sudo().search([
                ('survey_id', '=', survey_sudo.id),
                ('access_token', '=', answer_token)
            ], limit=1)
        return survey_sudo, answer_sudo

    def _check_validity(self, survey_token, answer_token, ensure_token=True):
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
        survey_sudo, answer_sudo = self._fetch_from_access_token(survey_token, answer_token)

        if not survey_sudo.exists():
            return 'survey_wrong'

        if answer_token and not answer_sudo:
            return 'token_wrong'

        if not answer_sudo and ensure_token:
            return 'token_required'
        if not answer_sudo and survey_sudo.access_mode == 'token':
            return 'token_required'

        if survey_sudo.users_login_required and request.env.user._is_public():
            return 'survey_auth'

        if (survey_sudo.state == 'closed' or survey_sudo.state == 'draft' or not survey_sudo.active) and (not answer_sudo or not answer_sudo.test_entry):
            return 'survey_closed'

        if (not survey_sudo.page_ids and survey_sudo.questions_layout == 'page_per_section') or not survey_sudo.question_ids:
            return 'survey_void'

        if answer_sudo and answer_sudo.deadline and answer_sudo.deadline < datetime.now():
            return 'answer_deadline'

        return True

    def _get_access_data(self, survey_token, answer_token, ensure_token=True):
        """ Get back data related to survey and user input, given the ID and access
        token provided by the route.

         : param ensure_token: whether user input existence should be enforced or not(see ``_check_validity``)
        """
        survey_sudo, answer_sudo = request.env['survey.survey'].sudo(), request.env['survey.user_input'].sudo()
        has_survey_access, can_answer = False, False

        validity_code = self._check_validity(survey_token, answer_token, ensure_token=ensure_token)
        if validity_code != 'survey_wrong':
            survey_sudo, answer_sudo = self._fetch_from_access_token(survey_token, answer_token)
            try:
                survey_user = survey_sudo.with_user(request.env.user)
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
            return request.render("survey.survey_void_content", {'survey': survey_sudo, 'answer': answer_sudo})
        elif error_key == 'survey_closed' and access_data['can_answer']:
            return request.render("survey.survey_closed_expired", {'survey': survey_sudo})
        elif error_key == 'survey_auth' and answer_sudo.access_token:
            if answer_sudo.partner_id and (answer_sudo.partner_id.user_ids or survey_sudo.users_can_signup):
                if answer_sudo.partner_id.user_ids:
                    answer_sudo.partner_id.signup_cancel()
                else:
                    answer_sudo.partner_id.signup_prepare(expiration=fields.Datetime.now() + relativedelta(days=1))
                redirect_url = answer_sudo.partner_id._get_signup_url_for_action(url='/survey/start/%s?answer_token=%s' % (survey_sudo.access_token, answer_sudo.access_token))[answer_sudo.partner_id.id]
            else:
                redirect_url = '/web/login?redirect=%s' % ('/survey/start/%s?answer_token=%s' % (survey_sudo.access_token, answer_sudo.access_token))
            return request.render("survey.survey_auth_required", {'survey': survey_sudo, 'redirect_url': redirect_url})
        elif error_key == 'answer_deadline' and answer_sudo.access_token:
            return request.render("survey.survey_closed_expired", {'survey': survey_sudo})

        return werkzeug.utils.redirect("/")

    @http.route('/survey/test/<string:survey_token>', type='http', auth='user', website=True)
    def survey_test(self, survey_token, **kwargs):
        """ Test mode for surveys: create a test answer, only for managers or officers
        testing their surveys """
        survey_sudo, dummy = self._fetch_from_access_token(survey_token, False)
        try:
            answer_sudo = survey_sudo._create_answer(user=request.env.user, test_entry=True)
        except:
            return werkzeug.utils.redirect('/')
        return request.redirect('/survey/start/%s?%s' % (survey_sudo.access_token, keep_query('*', answer_token=answer_sudo.access_token)))

    @http.route('/survey/retry/<string:survey_token>/<string:answer_token>', type='http', auth='public', website=True)
    def survey_retry(self, survey_token, answer_token, **post):
        """ This route is called whenever the user has attempts left and hits the 'Retry' button
        after failing the survey."""
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data['validity_code'] is not True:
            return self._redirect_with_error(access_data, access_data['validity_code'])

        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']
        if not answer_sudo:
            # attempts to 'retry' without having tried first
            return werkzeug.utils.redirect("/")

        try:
            retry_answer_sudo = survey_sudo._create_answer(
                user=request.env.user,
                partner=answer_sudo.partner_id,
                email=answer_sudo.email,
                invite_token=answer_sudo.invite_token,
                **self._prepare_retry_additional_values(answer_sudo)
            )
        except:
            return werkzeug.utils.redirect("/")
        return request.redirect('/survey/start/%s?%s' % (survey_sudo.access_token, keep_query('*', answer_token=retry_answer_sudo.access_token)))

    def _prepare_retry_additional_values(self, answer):
        return {
            'deadline': answer.deadline,
        }

    def _prepare_survey_finished_values(self, survey, answer, token=False):
        values = {'survey': survey, 'answer': answer}
        if token:
            values['token'] = token
        if survey.scoring_type != 'no_scoring' and survey.certification:
            values['graph_data'] = json.dumps(answer._prepare_statistics()[0])
        return values

    # ------------------------------------------------------------
    # TAKING SURVEY ROUTES
    # ------------------------------------------------------------

    @http.route('/survey/start/<string:survey_token>', type='http', auth='public', website=True)
    def survey_start(self, survey_token, answer_token=None, email=False, **post):
        """ Start a survey by providing
         * a token linked to a survey;
         * a token linked to an answer or generate a new token if access is allowed;
        """
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=False)
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
                survey_sudo.with_user(request.env.user).check_access_rights('read')
                survey_sudo.with_user(request.env.user).check_access_rule('read')
            except:
                return werkzeug.utils.redirect("/")
            else:
                return request.render("survey.survey_403_page", {'survey': survey_sudo})

        return request.redirect('/survey/%s/%s' % (survey_sudo.access_token, answer_sudo.access_token))

    def _prepare_survey_data(self, survey_sudo, answer_sudo, **post):
        """ This method prepares all the data needed for template rendering, in function of the survey user input state.
            :param post:
                - previous_page_id : come from the breadcrumb or the back button and force the next questions to load
                                     to be the previous ones. """
        data = {
            'survey': survey_sudo,
            'answer': answer_sudo,
            'breadcrumb_pages': [{
                'id': page.id,
                'title': page.title,
            } for page in survey_sudo.page_ids],
            'format_datetime': lambda dt: format_datetime(request.env, dt, dt_format=False),
            'format_date': lambda date: format_date(request.env, date)
        }

        page_or_question_key = 'question' if survey_sudo.questions_layout == 'page_per_question' else 'page'

        # Bypass all if page_id is specified (comes from breadcrumb or previous button)
        if 'previous_page_id' in post:
            previous_page_or_question_id = int(post['previous_page_id'])
            new_previous_id = survey_sudo._previous_page_or_question_id(answer_sudo, previous_page_or_question_id)
            data.update({
                page_or_question_key: request.env['survey.question'].sudo().browse(previous_page_or_question_id),
                'previous_page_id': new_previous_id
            })
            return data

        if answer_sudo.state == 'in_progress':
            page_or_question_id, is_last = survey_sudo.next_page_or_question(
                answer_sudo,
                answer_sudo.last_displayed_page_id.id if answer_sudo.last_displayed_page_id else 0)

            data.update({
                page_or_question_key: page_or_question_id,
            })
            if survey_sudo.questions_layout != 'one_page':
                data.update({
                    'previous_page_id': survey_sudo._previous_page_or_question_id(answer_sudo, page_or_question_id.id)
                })
            if is_last:
                data.update({'last': True})
        elif answer_sudo.state == 'done' or answer_sudo.is_time_limit_reached:  # Display success message
            return self._prepare_survey_finished_values(survey_sudo, answer_sudo)

        return data

    def _prepare_question_html(self, survey_sudo, answer_sudo, **post):
        """ Survey page navigation is done in AJAX. This function prepare the 'next page' to display in html
        and send back this html to the survey_form widget that will inject it into the page."""
        data = self._prepare_survey_data(survey_sudo, answer_sudo, **post)
        if answer_sudo.state == 'done':
            return request.env.ref('survey.survey_fill_form_done').render(data).decode('UTF-8')
        return request.env.ref('survey.survey_fill_form_in_progress').render(data).decode('UTF-8')

    @http.route('/survey/<string:survey_token>/<string:answer_token>', type='http', auth='public', website=True)
    def survey_display_page(self, survey_token, answer_token, **post):
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data['validity_code'] is not True:
            return self._redirect_with_error(access_data, access_data['validity_code'])

        return request.render('survey.survey_page_fill',
            self._prepare_survey_data(access_data['survey_sudo'], access_data['answer_sudo'], **post))

    @http.route('/survey/get_background_image/<string:survey_token>/<string:answer_token>', type='http', auth="public", website=True, sitemap=False)
    def survey_get_background(self, survey_token, answer_token):
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data['validity_code'] is not True:
            return werkzeug.exceptions.Forbidden()

        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']

        status, headers, image_base64 = request.env['ir.http'].sudo().binary_content(
            model='survey.survey', id=survey_sudo.id, field='background_image',
            default_mimetype='image/png')

        return Binary._content_image_get_response(status, headers, image_base64)

    # ----------------------------------------------------------------
    # JSON ROUTES to begin / continue survey (ajax navigation) + Tools
    # ----------------------------------------------------------------

    @http.route('/survey/begin/<string:survey_token>/<string:answer_token>', type='json', auth='public', website=True)
    def survey_begin(self, survey_token, answer_token, **post):
        """ Route used to start the survey user input and display the first survey page. """
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data['validity_code'] is not True:
            return {'error': access_data['validity_code']}
        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']

        if answer_sudo.state != "new":
            return {'error': _("The survey has already started.")}

        # init start date when user starts filling in the survey
        answer_sudo.write({
            'start_datetime': fields.Datetime.now(),
            'state': 'in_progress'
        })
        return self._prepare_question_html(survey_sudo, answer_sudo, **post)

    @http.route('/survey/submit/<string:survey_token>/<string:answer_token>', type='json', auth='public', website=True)
    def survey_submit(self, survey_token, answer_token, **post):
        """ Submit a page from the survey.
        This will take into account the validation errors and store the answers to the questions.
        If the time limit is reached, errors will be skipped, answers will be ignored and
        survey state will be forced to 'done'"""
        # Survey Validation
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data['validity_code'] is not True:
            return {'error': access_data['validity_code']}
        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']

        if answer_sudo.state == 'done':
            return {'error': 'unauthorized'}

        questions, page_or_question_id = survey_sudo._get_survey_questions(answer=answer_sudo,
                                                                           page_id=post.get('page_id'),
                                                                           question_id=post.get('question_id'))

        if not answer_sudo.test_entry and not survey_sudo._has_attempts_left(answer_sudo.partner_id, answer_sudo.email, answer_sudo.invite_token):
            # prevent cheating with users creating multiple 'user_input' before their last attempt
            return {'error': 'unauthorized'}

        if answer_sudo.is_time_limit_reached:
            time_limit = answer_sudo.start_datetime + timedelta(minutes=survey_sudo.time_limit)
            if fields.Datetime.now() > (time_limit + timedelta(seconds=10)):
                # prevent cheating with users blocking the JS timer and taking all their time to answer
                return {'error': 'unauthorized'}

        errors = {}
        # Prepare answers / comment by question, validate and save answers
        for question in questions:
            answer, comment = self._extract_comment_from_answers(question, post.get(str(question.id)))
            errors.update(question.validate_question(answer, comment))
            if not errors.get(question.id):
                answer_sudo.save_lines(question, answer, comment)

        if errors and not answer_sudo.is_time_limit_reached:
            return {'error': 'validation', 'fields': errors}

        if answer_sudo.is_time_limit_reached or survey_sudo.questions_layout == 'one_page':
            answer_sudo._mark_done()
        elif 'previous_page_id' in post:
            # Go back to specific page using the breadcrumb. Lines are saved and survey continues
            return self._prepare_question_html(survey_sudo, answer_sudo, **post)
        else:
            next_page, unused = request.env['survey.survey'].next_page_or_question(answer_sudo, page_or_question_id)
            vals = {'last_displayed_page_id': page_or_question_id}

            if next_page is None:
                answer_sudo._mark_done()
            else:
                vals.update({'state': 'in_progress'})

            answer_sudo.write(vals)

        return self._prepare_question_html(survey_sudo, answer_sudo)

    def _extract_comment_from_answers(self, question, answers):
        """ Answers is a custom structure depending of the question type
        that can contain question answers but also comments that need to be
        extracted before validating and saving answers.
        If multiple answers, they are listed in an array, except for matrix
        where answers are structured differently. See input and output for
        more info on data structures.
        :param question: survey.question
        :param answers:
          * question_type: free_text, text_box, numerical_box, date, datetime
            answers is a string containing the value
          * question_type: simple_choice with no comment
            answers is a string containing the value ('question_id_1')
          * question_type: simple_choice with comment
            ['question_id_1', {'comment': str}]
          * question_type: multiple choice
            ['question_id_1', 'question_id_2'] + [{'comment': str}] if holds a comment
          * question_type: matrix
            {'matrix_row_id_1': ['question_id_1', 'question_id_2'],
             'matrix_row_id_2': ['question_id_1', 'question_id_2']
            } + {'comment': str} if holds a comment
        :return: tuple(
          same structure without comment,
          extracted comment for given question
        ) """
        comment = None
        answers_no_comment = []
        if answers:
            if question.question_type == 'matrix':
                if 'comment' in answers:
                    comment = answers['comment'].strip()
                    answers.pop('comment')
                answers_no_comment = answers
            else:
                if not isinstance(answers, list):
                    answers = [answers]
                for answer in answers:
                    if 'comment' in answer:
                        comment = answer['comment'].strip()
                    else:
                        answers_no_comment.append(answer)
                if len(answers_no_comment) == 1:
                    answers_no_comment = answers_no_comment[0]
        return answers_no_comment, comment

    # ------------------------------------------------------------
    # COMPLETED SURVEY ROUTES
    # ------------------------------------------------------------

    @http.route('/survey/print/<string:survey_token>', type='http', auth='public', website=True, sitemap=False)
    def survey_print(self, survey_token, review=False, answer_token=None, **post):
        '''Display an survey in printable view; if <answer_token> is set, it will
        grab the answers of the user_input_id that has <answer_token>.'''
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=False)
        if access_data['validity_code'] is not True and (
                access_data['has_survey_access'] or
                access_data['validity_code'] not in ['token_required', 'survey_closed', 'survey_void']):
            return self._redirect_with_error(access_data, access_data['validity_code'])

        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']

        if survey_sudo.scoring_type == 'scoring_without_answers':
            return request.render("survey.survey_403_page", {'survey': survey_sudo})

        return request.render('survey.survey_page_print', {
            'review': review,
            'survey': survey_sudo,
            'answer': answer_sudo,
            'scoring_display_correction': survey_sudo.scoring_type == 'scoring_with_answers' and answer_sudo,
            'format_datetime': lambda dt: format_datetime(request.env, dt, dt_format=False),
            'format_date': lambda date: format_date(request.env, date)
        })

    @http.route(['/survey/<model("survey.survey"):survey>/get_certification_preview'], type="http", auth="user", methods=['GET'], website=True)
    def survey_get_certification_preview(self, survey, **kwargs):
        if not request.env.user.has_group('survey.group_survey_user'):
            raise werkzeug.exceptions.Forbidden()

        fake_user_input = survey._create_answer(user=request.env.user, test_entry=True)
        response = self._generate_report(fake_user_input, download=False)
        fake_user_input.sudo().unlink()
        return response

    @http.route(['/survey/<int:survey_id>/get_certification'], type='http', auth='user', methods=['GET'], website=True)
    def survey_get_certification(self, survey_id, **kwargs):
        """ The certification document can be downloaded as long as the user has succeeded the certification """
        survey = request.env['survey.survey'].sudo().search([
            ('id', '=', survey_id),
            ('certification', '=', True)
        ])

        if not survey:
            # no certification found
            return werkzeug.utils.redirect("/")

        succeeded_attempt = request.env['survey.user_input'].sudo().search([
            ('partner_id', '=', request.env.user.partner_id.id),
            ('survey_id', '=', survey_id),
            ('scoring_success', '=', True)
        ], limit=1)

        if not succeeded_attempt:
            raise UserError(_("The user has not succeeded the certification"))

        return self._generate_report(succeeded_attempt, download=True)

    # ------------------------------------------------------------
    # REPORTING SURVEY ROUTES AND TOOLS
    # ------------------------------------------------------------

    @http.route('/survey/results/<model("survey.survey"):survey>', type='http', auth='user', website=True)
    def survey_report(self, survey, answer_token=None, **post):
        """ Display survey Results & Statistics for given survey.

        New structure: {
            'survey': current survey browse record,
            'question_and_page_data': see ``SurveyQuestion._prepare_statistics()``,
            'survey_data'= see ``SurveySurvey._prepare_statistics()``
            'search_filters': [],
            'search_finished': either filter on finished inputs only or not,
        }
        """
        user_input_lines, search_filters = self._extract_filters_data(survey, post)
        survey_data = survey._prepare_statistics(user_input_lines)
        question_and_page_data = survey.question_and_page_ids._prepare_statistics(user_input_lines)

        return request.render('survey.survey_page_statistics', {
            # survey and its statistics
            'survey': survey,
            'question_and_page_data': question_and_page_data,
            'survey_data': survey_data,
            # search
            'search_filters': search_filters,
            'search_finished': post.get('finished') == 'true',
        })

    def _generate_report(self, user_input, download=True):
        report = request.env.ref('survey.certification_report').sudo().render_qweb_pdf([user_input.id], data={'report_type': 'pdf'})[0]

        report_content_disposition = content_disposition('Certification.pdf')
        if not download:
            content_split = report_content_disposition.split(';')
            content_split[0] = 'inline'
            report_content_disposition = ';'.join(content_split)

        return request.make_response(report, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(report)),
            ('Content-Disposition', report_content_disposition),
        ])

    def _extract_filters_data(self, survey, post):
        search_filters = []
        line_filter_domain, line_choices = [], []
        for data in post.get('filters', '').split('|'):
            try:
                row_id, answer_id = (int(item) for item in data.split(','))
            except:
                pass
            else:
                if row_id and answer_id:
                    line_filter_domain = expression.AND([
                        ['&', ('matrix_row_id', '=', row_id), ('suggested_answer_id', '=', answer_id)],
                        line_filter_domain
                    ])
                    answers = request.env['survey.question.answer'].browse([row_id, answer_id])
                elif answer_id:
                    line_choices.append(answer_id)
                    answers = request.env['survey.question.answer'].browse([answer_id])
                if answer_id:
                    search_filters.append({
                        'question': answers[0].question_id.title,
                        'answers': '%s%s' % (answers[0].value, ': %s' % answers[1].value if len(answers) > 1 else '')
                    })
        if line_choices:
            line_filter_domain = expression.AND([[('suggested_answer_id', 'in', line_choices)], line_filter_domain])

        user_input_domain = ['&', ('test_entry', '=', False), ('survey_id', '=', survey.id)]
        if line_filter_domain:
            matching_line_ids = request.env['survey.user_input.line'].sudo().search(line_filter_domain).ids
            user_input_domain = expression.AND([
                [('user_input_line_ids', 'in', matching_line_ids)],
                user_input_domain
            ])
        if post.get('finished'):
            user_input_domain = expression.AND([[('state', '=', 'done')], user_input_domain])
        else:
            user_input_domain = expression.AND([[('state', '!=', 'new')], user_input_domain])
        user_input_lines = request.env['survey.user_input'].sudo().search(user_input_domain).mapped('user_input_line_ids')

        return user_input_lines, search_filters
