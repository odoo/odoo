# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import werkzeug

from collections import defaultdict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import fields, http, SUPERUSER_ID, _
from odoo.exceptions import UserError
from odoo.http import request, content_disposition
from odoo.osv import expression
from odoo.tools import format_datetime, format_date, is_html_empty
from odoo.addons.base.models.ir_qweb import keep_query

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

    def _check_validity(self, survey_token, answer_token, ensure_token=True, check_partner=True):
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

        :param check_partner: Whether we must check that the partner associated to the target
          answer corresponds to the active user.
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

        if not survey_sudo.active and (not answer_sudo or not answer_sudo.test_entry):
            return 'survey_closed'

        if (not survey_sudo.page_ids and survey_sudo.questions_layout == 'page_per_section') or not survey_sudo.question_ids:
            return 'survey_void'

        if answer_sudo and check_partner:
            if request.env.user._is_public() and answer_sudo.partner_id and not answer_token:
                # answers from public user should not have any partner_id; this indicates probably a cookie issue
                return 'answer_wrong_user'
            if not request.env.user._is_public() and answer_sudo.partner_id != request.env.user.partner_id:
                # partner mismatch, probably a cookie issue
                return 'answer_wrong_user'

        if answer_sudo and answer_sudo.deadline and answer_sudo.deadline < datetime.now():
            return 'answer_deadline'

        return True

    def _get_access_data(self, survey_token, answer_token, ensure_token=True, check_partner=True):
        """ Get back data related to survey and user input, given the ID and access
        token provided by the route.

         : param ensure_token: whether user input existence should be enforced or not(see ``_check_validity``)
         : param check_partner: whether the partner of the target answer should be checked (see ``_check_validity``)
        """
        survey_sudo, answer_sudo = request.env['survey.survey'].sudo(), request.env['survey.user_input'].sudo()
        has_survey_access, can_answer = False, False

        validity_code = self._check_validity(survey_token, answer_token, ensure_token=ensure_token, check_partner=check_partner)
        if validity_code != 'survey_wrong':
            survey_sudo, answer_sudo = self._fetch_from_access_token(survey_token, answer_token)
            try:
                survey_user = survey_sudo.with_user(request.env.user)
                survey_user.check_access_rights('read', raise_exception=True)
                survey_user.check_access_rule('read')
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
        elif error_key == 'survey_auth':
            if not answer_sudo:  # survey is not even started
                redirect_url = '/web/login?redirect=/survey/start/%s' % survey_sudo.access_token
            elif answer_sudo.access_token:  # survey is started but user is not logged in anymore.
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
        elif error_key in ['answer_wrong_user', 'token_wrong']:
            return request.render("survey.survey_access_error", {'survey': survey_sudo})

        return request.redirect("/")

    # ------------------------------------------------------------
    # TEST / RETRY SURVEY ROUTES
    # ------------------------------------------------------------

    @http.route('/survey/test/<string:survey_token>', type='http', auth='user', website=True)
    def survey_test(self, survey_token, **kwargs):
        """ Test mode for surveys: create a test answer, only for managers or officers
        testing their surveys """
        survey_sudo, dummy = self._fetch_from_access_token(survey_token, False)
        try:
            answer_sudo = survey_sudo._create_answer(user=request.env.user, test_entry=True)
        except:
            return request.redirect('/')
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
            return request.redirect("/")

        try:
            retry_answer_sudo = survey_sudo._create_answer(
                user=request.env.user,
                partner=answer_sudo.partner_id,
                email=answer_sudo.email,
                invite_token=answer_sudo.invite_token,
                test_entry=answer_sudo.test_entry,
                **self._prepare_retry_additional_values(answer_sudo)
            )
        except:
            return request.redirect("/")
        return request.redirect('/survey/start/%s?%s' % (survey_sudo.access_token, keep_query('*', answer_token=retry_answer_sudo.access_token)))

    def _prepare_retry_additional_values(self, answer):
        return {
            'deadline': answer.deadline,
        }

    def _prepare_survey_finished_values(self, survey, answer, token=False):
        values = {'survey': survey, 'answer': answer}
        if token:
            values['token'] = token
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
        # Get the current answer token from cookie
        answer_from_cookie = False
        if not answer_token:
            answer_token = request.httprequest.cookies.get('survey_%s' % survey_token)
            answer_from_cookie = bool(answer_token)

        access_data = self._get_access_data(survey_token, answer_token, ensure_token=False)

        if answer_from_cookie and access_data['validity_code'] in ('answer_wrong_user', 'token_wrong'):
            # If the cookie had been generated for another user or does not correspond to any existing answer object
            # (probably because it has been deleted), ignore it and redo the check.
            # The cookie will be replaced by a legit value when resolving the URL, so we don't clean it further here.
            access_data = self._get_access_data(survey_token, None, ensure_token=False)

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
                return request.redirect("/")
            else:
                return request.render("survey.survey_403_page", {'survey': survey_sudo})

        return request.redirect('/survey/%s/%s' % (survey_sudo.access_token, answer_sudo.access_token))

    def _prepare_survey_data(self, survey_sudo, answer_sudo, **post):
        """ This method prepares all the data needed for template rendering, in function of the survey user input state.
            :param post:
                - previous_page_id : come from the breadcrumb or the back button and force the next questions to load
                                     to be the previous ones.
                - next_skipped_page : force the display of next skipped question or page if any."""
        data = {
            'is_html_empty': is_html_empty,
            'survey': survey_sudo,
            'answer': answer_sudo,
            'skipped_questions': answer_sudo._get_skipped_questions(),
            'breadcrumb_pages': [{
                'id': page.id,
                'title': page.title,
            } for page in survey_sudo.page_ids],
            'format_datetime': lambda dt: format_datetime(request.env, dt, dt_format=False),
            'format_date': lambda date: format_date(request.env, date)
        }
        if survey_sudo.questions_layout != 'page_per_question':
            triggering_answers_by_question, triggered_questions_by_answer, selected_answers = answer_sudo._get_conditional_values()
            data.update({
                'triggering_answers_by_question': {
                    question.id: triggering_answers.ids
                    for question, triggering_answers in triggering_answers_by_question.items() if triggering_answers
                },
                'triggered_questions_by_answer': {
                    answer.id: triggered_questions.ids
                    for answer, triggered_questions in triggered_questions_by_answer.items()
                },
                'selected_answers': selected_answers.ids
            })

        if not answer_sudo.is_session_answer and survey_sudo.is_time_limited and answer_sudo.start_datetime:
            data.update({
                'server_time': fields.Datetime.now(),
                'timer_start': answer_sudo.start_datetime.isoformat(),
                'time_limit_minutes': survey_sudo.time_limit
            })

        page_or_question_key = 'question' if survey_sudo.questions_layout == 'page_per_question' else 'page'

        # Bypass all if page_id is specified (comes from breadcrumb or previous button)
        if 'previous_page_id' in post:
            previous_page_or_question_id = int(post['previous_page_id'])
            new_previous_id = survey_sudo._get_next_page_or_question(answer_sudo, previous_page_or_question_id, go_back=True).id
            page_or_question = request.env['survey.question'].sudo().browse(previous_page_or_question_id)
            data.update({
                page_or_question_key: page_or_question,
                'previous_page_id': new_previous_id,
                'has_answered': answer_sudo.user_input_line_ids.filtered(lambda line: line.question_id.id == new_previous_id),
                'can_go_back': survey_sudo._can_go_back(answer_sudo, page_or_question),
            })
            return data

        if answer_sudo.state == 'in_progress':
            next_page_or_question = None
            if answer_sudo.is_session_answer:
                next_page_or_question = survey_sudo.session_question_id
            else:
                if 'next_skipped_page' in post:
                    next_page_or_question = answer_sudo._get_next_skipped_page_or_question()
                if not next_page_or_question:
                    next_page_or_question = survey_sudo._get_next_page_or_question(
                        answer_sudo,
                        answer_sudo.last_displayed_page_id.id if answer_sudo.last_displayed_page_id else 0)
                    # fallback to skipped page so that there is a next_page_or_question otherwise this should be a submit
                    if not next_page_or_question:
                        next_page_or_question = answer_sudo._get_next_skipped_page_or_question()

                if next_page_or_question:
                    if answer_sudo.survey_first_submitted:
                        survey_last = answer_sudo._is_last_skipped_page_or_question(next_page_or_question)
                    else:
                        survey_last = survey_sudo._is_last_page_or_question(answer_sudo, next_page_or_question)
                    data.update({'survey_last': survey_last})

            if answer_sudo.is_session_answer and next_page_or_question.is_time_limited:
                data.update({
                    'timer_start': survey_sudo.session_question_start_time.isoformat(),
                    'time_limit_minutes': next_page_or_question.time_limit / 60
                })

            data.update({
                page_or_question_key: next_page_or_question,
                'has_answered': answer_sudo.user_input_line_ids.filtered(lambda line: line.question_id == next_page_or_question),
                'can_go_back': survey_sudo._can_go_back(answer_sudo, next_page_or_question),
            })
            if survey_sudo.questions_layout != 'one_page':
                data.update({
                    'previous_page_id': survey_sudo._get_next_page_or_question(answer_sudo, next_page_or_question.id, go_back=True).id
                })
        elif answer_sudo.state == 'done' or answer_sudo.survey_time_limit_reached:
            # Display success message
            return self._prepare_survey_finished_values(survey_sudo, answer_sudo)

        return data

    def _prepare_question_html(self, survey_sudo, answer_sudo, **post):
        """ Survey page navigation is done in AJAX. This function prepare the 'next page' to display in html
        and send back this html to the survey_form widget that will inject it into the page.
        Background url must be given to the caller in order to process its refresh as we don't have the next question
        object at frontend side."""
        survey_data = self._prepare_survey_data(survey_sudo, answer_sudo, **post)

        if answer_sudo.state == 'done':
            survey_content = request.env['ir.qweb']._render('survey.survey_fill_form_done', survey_data)
        else:
            survey_content = request.env['ir.qweb']._render('survey.survey_fill_form_in_progress', survey_data)

        survey_progress = False
        if answer_sudo.state == 'in_progress' and not survey_data.get('question', request.env['survey.question']).is_page:
            if survey_sudo.questions_layout == 'page_per_section':
                page_ids = survey_sudo.page_ids.ids
                survey_progress = request.env['ir.qweb']._render('survey.survey_progression', {
                    'survey': survey_sudo,
                    'page_ids': page_ids,
                    'page_number': page_ids.index(survey_data['page'].id) + (1 if survey_sudo.progression_mode == 'number' else 0)
                })
            elif survey_sudo.questions_layout == 'page_per_question':
                page_ids = (answer_sudo.predefined_question_ids.ids
                            if not answer_sudo.is_session_answer and survey_sudo.questions_selection == 'random'
                            else survey_sudo.question_ids.ids)
                survey_progress = request.env['ir.qweb']._render('survey.survey_progression', {
                    'survey': survey_sudo,
                    'page_ids': page_ids,
                    'page_number': page_ids.index(survey_data['question'].id)
                })

        background_image_url = survey_sudo.background_image_url
        if 'question' in survey_data:
            background_image_url = survey_data['question'].background_image_url
        elif 'page' in survey_data:
            background_image_url = survey_data['page'].background_image_url

        return {
            'has_skipped_questions': any(answer_sudo._get_skipped_questions()),
            'survey_content': survey_content,
            'survey_progress': survey_progress,
            'survey_navigation': request.env['ir.qweb']._render('survey.survey_navigation', survey_data),
            'background_image_url': background_image_url
        }

    @http.route('/survey/<string:survey_token>/<string:answer_token>', type='http', auth='public', website=True)
    def survey_display_page(self, survey_token, answer_token, **post):
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data['validity_code'] is not True:
            return self._redirect_with_error(access_data, access_data['validity_code'])

        answer_sudo = access_data['answer_sudo']
        if answer_sudo.state != 'done' and answer_sudo.survey_time_limit_reached:
            answer_sudo._mark_done()

        return request.render('survey.survey_page_fill',
            self._prepare_survey_data(access_data['survey_sudo'], answer_sudo, **post))

    # --------------------------------------------------------------------------
    # ROUTES to handle question images + survey background transitions + Tool
    # --------------------------------------------------------------------------

    @http.route('/survey/<string:survey_token>/get_background_image',
                type='http', auth="public", website=True, sitemap=False)
    def survey_get_background(self, survey_token):
        survey_sudo, dummy = self._fetch_from_access_token(survey_token, False)
        return request.env['ir.binary']._get_image_stream_from(
            survey_sudo, 'background_image'
        ).get_response()

    @http.route('/survey/<string:survey_token>/<int:section_id>/get_background_image',
                type='http', auth="public", website=True, sitemap=False)
    def survey_section_get_background(self, survey_token, section_id):
        survey_sudo, dummy = self._fetch_from_access_token(survey_token, False)

        section = survey_sudo.page_ids.filtered(lambda q: q.id == section_id)
        if not section:
            # trying to access a question that is not in this survey
            raise werkzeug.exceptions.Forbidden()

        return request.env['ir.binary']._get_image_stream_from(
            section, 'background_image'
        ).get_response()

    @http.route('/survey/get_question_image/<string:survey_token>/<string:answer_token>/<int:question_id>/<int:suggested_answer_id>', type='http', auth="public", website=True, sitemap=False)
    def survey_get_question_image(self, survey_token, answer_token, question_id, suggested_answer_id):
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data['validity_code'] is not True:
            return werkzeug.exceptions.Forbidden()

        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']

        suggested_answer = False
        if int(question_id) in survey_sudo.question_ids.ids:
            suggested_answer = request.env['survey.question.answer'].sudo().search([
                ('id', '=', int(suggested_answer_id)),
                ('question_id', '=', int(question_id)),
                ('question_id.survey_id', '=', survey_sudo.id),
            ])

        if not suggested_answer:
            return werkzeug.exceptions.NotFound()

        return request.env['ir.binary']._get_image_stream_from(
            suggested_answer, 'value_image'
        ).get_response()

    # ----------------------------------------------------------------
    # JSON ROUTES to begin / continue survey (ajax navigation) + Tools
    # ----------------------------------------------------------------

    @http.route('/survey/begin/<string:survey_token>/<string:answer_token>', type='json', auth='public', website=True)
    def survey_begin(self, survey_token, answer_token, **post):
        """ Route used to start the survey user input and display the first survey page.
        Returns an empty dict for the correct answers and the first page html. """
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data['validity_code'] is not True:
            return {}, {'error': access_data['validity_code']}
        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']

        if answer_sudo.state != "new":
            return {}, {'error': _("The survey has already started.")}

        answer_sudo._mark_in_progress()
        return {}, self._prepare_question_html(survey_sudo, answer_sudo, **post)

    @http.route('/survey/next_question/<string:survey_token>/<string:answer_token>', type='json', auth='public', website=True)
    def survey_next_question(self, survey_token, answer_token, **post):
        """ Method used to display the next survey question in an ongoing session.
        Triggered on all attendees screens when the host goes to the next question. """
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data['validity_code'] is not True:
            return {}, {'error': access_data['validity_code']}
        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']

        if answer_sudo.state == 'new' and answer_sudo.is_session_answer:
            answer_sudo._mark_in_progress()

        return {}, self._prepare_question_html(survey_sudo, answer_sudo, **post)

    @http.route('/survey/submit/<string:survey_token>/<string:answer_token>', type='json', auth='public', website=True)
    def survey_submit(self, survey_token, answer_token, **post):
        """ Submit a page from the survey.
        This will take into account the validation errors and store the answers to the questions.
        If the time limit is reached, errors will be skipped, answers will be ignored and
        survey state will be forced to 'done'.
        Also returns the correct answers if the scoring type is 'scoring_with_answers_after_page'."""
        # Survey Validation
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data['validity_code'] is not True:
            return {}, {'error': access_data['validity_code']}
        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']

        if answer_sudo.state == 'done':
            return {}, {'error': 'unauthorized'}

        questions, page_or_question_id = survey_sudo._get_survey_questions(answer=answer_sudo,
                                                                           page_id=post.get('page_id'),
                                                                           question_id=post.get('question_id'))

        if not answer_sudo.test_entry and not survey_sudo._has_attempts_left(answer_sudo.partner_id, answer_sudo.email, answer_sudo.invite_token):
            # prevent cheating with users creating multiple 'user_input' before their last attempt
            return {}, {'error': 'unauthorized'}

        if answer_sudo.survey_time_limit_reached or answer_sudo.question_time_limit_reached:
            if answer_sudo.question_time_limit_reached:
                time_limit = survey_sudo.session_question_start_time + relativedelta(
                    seconds=survey_sudo.session_question_id.time_limit
                )
                time_limit += timedelta(seconds=3)
            else:
                time_limit = answer_sudo.start_datetime + timedelta(minutes=survey_sudo.time_limit)
                time_limit += timedelta(seconds=10)
            if fields.Datetime.now() > time_limit:
                # prevent cheating with users blocking the JS timer and taking all their time to answer
                return {}, {'error': 'unauthorized'}

        errors = {}
        # Prepare answers / comment by question, validate and save answers
        for question in questions:
            inactive_questions = request.env['survey.question'] if answer_sudo.is_session_answer else answer_sudo._get_inactive_conditional_questions()
            if question in inactive_questions:  # if question is inactive, skip validation and save
                continue
            answer, comment = self._extract_comment_from_answers(question, post.get(str(question.id)))
            errors.update(question.validate_question(answer, comment))
            if not errors.get(question.id):
                answer_sudo._save_lines(question, answer, comment, overwrite_existing=survey_sudo.users_can_go_back or question.save_as_nickname or question.save_as_email)

        if errors and not (answer_sudo.survey_time_limit_reached or answer_sudo.question_time_limit_reached):
            return {}, {'error': 'validation', 'fields': errors}

        if not answer_sudo.is_session_answer:
            answer_sudo._clear_inactive_conditional_answers()

        # Get the page questions correct answers if scoring type is scoring after page
        correct_answers = {}
        if survey_sudo.scoring_type == 'scoring_with_answers_after_page':
            scorable_questions = (questions - answer_sudo._get_inactive_conditional_questions()).filtered('is_scored_question')
            correct_answers = scorable_questions._get_correct_answers()

        if answer_sudo.survey_time_limit_reached or survey_sudo.questions_layout == 'one_page':
            answer_sudo._mark_done()
        elif 'previous_page_id' in post:
            # when going back, save the last displayed to reload the survey where the user left it.
            answer_sudo.last_displayed_page_id = post['previous_page_id']
            # Go back to specific page using the breadcrumb. Lines are saved and survey continues
            return correct_answers, self._prepare_question_html(survey_sudo, answer_sudo, **post)
        elif 'next_skipped_page_or_question' in post:
            answer_sudo.last_displayed_page_id = page_or_question_id
            return correct_answers, self._prepare_question_html(survey_sudo, answer_sudo, next_skipped_page=True)
        else:
            if not answer_sudo.is_session_answer:
                page_or_question = request.env['survey.question'].sudo().browse(page_or_question_id)
                if answer_sudo.survey_first_submitted and answer_sudo._is_last_skipped_page_or_question(page_or_question):
                    next_page = request.env['survey.question']
                else:
                    next_page = survey_sudo._get_next_page_or_question(answer_sudo, page_or_question_id)
                if not next_page:
                    if survey_sudo.users_can_go_back and answer_sudo.user_input_line_ids.filtered(
                            lambda a: a.skipped and a.question_id.constr_mandatory):
                        answer_sudo.write({
                            'last_displayed_page_id': page_or_question_id,
                            'survey_first_submitted': True,
                        })
                        return correct_answers, self._prepare_question_html(survey_sudo, answer_sudo, next_skipped_page=True)
                    else:
                        answer_sudo._mark_done()

            answer_sudo.last_displayed_page_id = page_or_question_id

        return correct_answers, self._prepare_question_html(survey_sudo, answer_sudo)

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
                    if isinstance(answer, dict) and 'comment' in answer:
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
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=False, check_partner=False)
        if access_data['validity_code'] is not True and (
                access_data['has_survey_access'] or
                access_data['validity_code'] not in ['token_required', 'survey_closed', 'survey_void', 'answer_deadline']):
            return self._redirect_with_error(access_data, access_data['validity_code'])

        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']
        return request.render('survey.survey_page_print', {
            'is_html_empty': is_html_empty,
            'review': review,
            'survey': survey_sudo,
            'answer': answer_sudo if survey_sudo.scoring_type != 'scoring_without_answers' else answer_sudo.browse(),
            'questions_to_display': answer_sudo._get_print_questions(),
            'scoring_display_correction': survey_sudo.scoring_type in ['scoring_with_answers', 'scoring_with_answers_after_page'] and answer_sudo,
            'format_datetime': lambda dt: format_datetime(request.env, dt, dt_format=False),
            'format_date': lambda date: format_date(request.env, date),
            'graph_data': json.dumps(answer_sudo._prepare_statistics()[answer_sudo])
                              if answer_sudo and survey_sudo.scoring_type in ['scoring_with_answers', 'scoring_with_answers_after_page'] else False,
        })

    @http.route('/survey/<model("survey.survey"):survey>/certification_preview', type="http", auth="user", website=True)
    def show_certification_pdf(self, survey, **kwargs):
        preview_url = '/survey/%s/get_certification_preview' % survey.id
        return request.render('survey.certification_preview', {
            'preview_url': preview_url,
            'page_title': survey.title,
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
            return request.redirect("/")

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
            'search_passed': either filter on passed inputs only or not,
            'search_failed': either filter on failed inputs only or not,
        }
        """
        user_input_lines, search_filters = self._extract_filters_data(survey, post)
        survey_data = survey._prepare_statistics(user_input_lines)
        question_and_page_data = survey.question_and_page_ids._prepare_statistics(user_input_lines)

        template_values = {
            # survey and its statistics
            'survey': survey,
            'question_and_page_data': question_and_page_data,
            'survey_data': survey_data,
            # search
            'search_filters': search_filters,
            'search_finished': post.get('finished') == 'true',
            'search_failed': post.get('failed') == 'true',
            'search_passed': post.get('passed') == 'true',
        }

        if survey.session_show_leaderboard:
            template_values['leaderboard'] = survey._prepare_leaderboard_values()

        return request.render('survey.survey_page_statistics', template_values)

    def _generate_report(self, user_input, download=True):
        report = request.env["ir.actions.report"].sudo()._render_qweb_pdf('survey.certification_report', [user_input.id], data={'report_type': 'pdf'})[0]

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

    def _get_results_page_user_input_domain(self, survey, **post):
        user_input_domain = ['&', ('test_entry', '=', False), ('survey_id', '=', survey.id)]
        if post.get('finished'):
            user_input_domain = expression.AND([[('state', '=', 'done')], user_input_domain])
        else:
            user_input_domain = expression.AND([[('state', '!=', 'new')], user_input_domain])
        if post.get('failed'):
            user_input_domain = expression.AND([[('scoring_success', '=', False)], user_input_domain])
        elif post.get('passed'):
            user_input_domain = expression.AND([[('scoring_success', '=', True)], user_input_domain])

        return user_input_domain

    def _extract_filters_data(self, survey, post):
        """ Extracts the filters from the URL to returns the related user_input_lines and
        the parameters used to render/remove the filters on the results page (search_filters).

        The matching user_input_lines are all the lines tied to the user inputs which respect
        the survey base domain and which have lines matching all the filters.
        For example, with the filter 'Where do you live?|Brussels', we need to display ALL the lines
        of the survey user inputs which have answered 'Brussels' to this question.

        :return (recordset, List[dict]): all matching user input lines, each search filter data
        """
        user_input_line_subdomains = []
        search_filters = []

        answer_by_column, user_input_lines_ids = self._get_filters_from_post(post)

        # Matrix, Multiple choice, Simple choice filters
        if answer_by_column:
            answer_ids, row_ids = [], []
            for answer_column_id, answer_row_ids in answer_by_column.items():
                answer_ids.append(answer_column_id)
                row_ids += answer_row_ids

            answers_and_rows = request.env['survey.question.answer'].browse(answer_ids+row_ids)
            # For performance, accessing 'a.matrix_question_id' caches all useful fields of the
            # answers and rows records, avoiding unnecessary queries.
            answers = answers_and_rows.filtered(lambda a: not a.matrix_question_id)

            for answer in answers:
                if not answer_by_column[answer.id]:
                    # Simple/Multiple choice
                    user_input_line_subdomains.append(answer._get_answer_matching_domain())
                    search_filters.append(self._prepare_search_filter_answer(answer))
                else:
                    # Matrix
                    for row_id in answer_by_column[answer.id]:
                        row = answers_and_rows.filtered(lambda answer_or_row: answer_or_row.id == row_id)
                        user_input_line_subdomains.append(answer._get_answer_matching_domain(row_id))
                        search_filters.append(self._prepare_search_filter_answer(answer, row))

        # Char_box, Text_box, Numerical_box, Date, Datetime filters
        if user_input_lines_ids:
            user_input_lines = request.env['survey.user_input.line'].browse(user_input_lines_ids)
            for input_line in user_input_lines:
                user_input_line_subdomains.append(input_line._get_answer_matching_domain())
                search_filters.append(self._prepare_search_filter_input_line(input_line))

        # Compute base domain
        user_input_domain = self._get_results_page_user_input_domain(survey, **post)

        # Add filters domain to the base domain
        if user_input_line_subdomains:
            all_required_lines_domains = [
                [('user_input_line_ids', 'in', request.env['survey.user_input.line'].sudo()._search(subdomain))]
                for subdomain in user_input_line_subdomains
            ]
            user_input_domain = expression.AND([user_input_domain, *all_required_lines_domains])

        # Get the matching user input lines
        user_inputs_query = request.env['survey.user_input'].sudo()._search(user_input_domain)
        user_input_lines = request.env['survey.user_input.line'].search([('user_input_id', 'in', user_inputs_query)])

        return user_input_lines, search_filters

    def _get_filters_from_post(self, post):
        """ Extract the filters from post depending on the model that needs to be called to retrieve the filtered answer data.
        Simple choice and multiple choice question types are mapped onto empty row_id.
        Input/output example with respectively matrix, simple_choice and char_box filters:
            input: 'A,1,24|A,0,13|L,0,36'
            output:
                answer_by_column: {24: [1], 13: []}
                user_input_lines_ids: [36]

        * Model short key = 'A' : Match a `survey.question.answer` record (simple_choice, multiple_choice, matrix)
        * Model short key = 'L' : Match a `survey.user_input.line` record (char_box, text_box, numerical_box, date, datetime)
        :rtype: (collections.defaultdict[int, list[int]], list[int])
        """
        answer_by_column = defaultdict(list)
        user_input_lines_ids = []

        for data in post.get('filters', '').split('|'):
            if not data:
                break
            model_short_key, row_id, answer_id = data.split(',')
            row_id, answer_id = int(row_id), int(answer_id)
            if model_short_key == 'A':
                if row_id:
                    answer_by_column[answer_id].append(row_id)
                else:
                    answer_by_column[answer_id] = []
            elif model_short_key == 'L' and not row_id:
                user_input_lines_ids.append(answer_id)

        return answer_by_column, user_input_lines_ids

    def _prepare_search_filter_answer(self, answer, row=False):
        """ Format parameters used to render/remove this filter on the results page."""
        return {
            'question_id': answer.question_id.id,
            'question': answer.question_id.title,
            'row_id': row.id if row else 0,
            'answer': '%s : %s' % (row.value, answer.value) if row else answer.value,
            'model_short_key': 'A',
            'record_id': answer.id,
        }

    def _prepare_search_filter_input_line(self, user_input_line):
        """ Format parameters used to render/remove this filter on the results page."""
        return {
            'question_id': user_input_line.question_id.id,
            'question': user_input_line.question_id.title,
            'row_id': 0,
            'answer': user_input_line._get_answer_value(),
            'model_short_key': 'L',
            'record_id': user_input_line.id,
        }
