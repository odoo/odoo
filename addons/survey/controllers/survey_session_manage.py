# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import json

from dateutil.relativedelta import relativedelta
from werkzeug.exceptions import NotFound

from odoo import fields, http
from odoo.http import request
from odoo.tools import is_html_empty


class UserInputSession(http.Controller):
    def _fetch_from_token(self, survey_token):
        """ Check that given survey_token matches a survey 'access_token'.
        Unlike the regular survey controller, user trying to access the survey must have full access rights! """
        return request.env['survey.survey'].search([('access_token', '=', survey_token)])

    def _fetch_from_session_code(self, session_code):
        """ Matches a survey against a passed session_code, and checks if it is valid.
        If it is valid, returns the start url. Else, the error type."""
        if not session_code:
            return None, {'error': 'survey_wrong'}
        survey = request.env['survey.survey'].sudo().search([('session_code', '=', session_code)], limit=1)
        if not survey or survey.certification:
            return None, {'error': 'survey_wrong'}
        if survey.session_state in ['ready', 'in_progress']:
            return survey, None
        if request.env.user.has_group("survey.group_survey_user"):
            return None, {'error': 'survey_session_not_launched', 'survey_id': survey.id}
        return None, {'error': 'survey_session_not_launched'}

    # ------------------------------------------------------------
    # SURVEY SESSION MANAGEMENT
    # ------------------------------------------------------------

    @http.route('/survey/session/manage/<string:survey_token>', type='http', auth='user', website=True)
    def survey_session_manage(self, survey_token, **kwargs):
        """ Main route used by the host to 'manager' the session.
        - If the state of the session is 'ready'
          We render a template allowing the host to showcase the different options of the session
          and to actually start the session.
          If there are no questions, a "void content" is displayed instead to avoid displaying a
          blank survey.
        - If the state of the session is 'in_progress'
          We render a template allowing the host to show the question results, display the attendees
          leaderboard or go to the next question of the session. """

        survey = self._fetch_from_token(survey_token)

        if not survey:
            return NotFound()

        if survey.session_state == 'ready':
            if not survey.question_ids:
                return request.render('survey.survey_void_content', {
                    'survey': survey,
                    'answer': request.env['survey.user_input'],
                })
            return request.render('survey.user_input_session_open', {
                'survey': survey
            })
        # Note that at this stage survey.session_state can be False meaning that the survey has ended (session closed)
        return request.render('survey.user_input_session_manage', self._prepare_manage_session_values(survey))

    @http.route('/survey/session/next_question/<string:survey_token>', type='json', auth='user', website=True)
    def survey_session_next_question(self, survey_token, go_back=False, **kwargs):
        """ This route is called when the host goes to the next question of the session.

        It's not a regular 'request.render' route because we handle the transition between
        questions using a AJAX call to be able to display a bioutiful fade in/out effect.

        It triggers the next question of the session.

        We artificially add 1 second to the 'current_question_start_time' to account for server delay.
        As the timing can influence the attendees score, we try to be fair with everyone by giving them
        an extra second before we start counting down.

        Frontend should take the delay into account by displaying the appropriate animations.

        Writing the next question on the survey is sudo'ed to avoid potential access right issues.
        e.g: a survey user can create a live session from any survey but they can only write
        on their own survey.

        In addition to return a pre-rendered html template with the next question, we also return the background
        to display. Background image depends on the next question to display and cannot be extracted from the
        html rendered question template. The background needs to be changed at frontend side on a specific selector."""

        survey = self._fetch_from_token(survey_token)

        if not survey or not survey.session_state:
            # no open session
            return {}

        if survey.session_state == 'ready':
            survey._session_open()

        next_question = survey._get_session_next_question(go_back)

        # using datetime.datetime because we want the millis portion
        if next_question:
            now = datetime.datetime.now()
            survey.sudo().write({
                'session_question_id': next_question.id,
                'session_question_start_time': fields.Datetime.now() + relativedelta(seconds=1)
            })
            request.env['bus.bus']._sendone(survey.access_token, 'next_question', {
                'question_start': now.timestamp()
            })

            template_values = self._prepare_manage_session_values(survey)
            template_values['is_rpc_call'] = True

            return {
                'background_image_url': survey.session_question_id.background_image_url,
                'question_html': request.env['ir.qweb']._render('survey.user_input_session_manage_content', template_values)
            }
        else:
            return {}

    @http.route('/survey/session/results/<string:survey_token>', type='json', auth='user', website=True)
    def survey_session_results(self, survey_token, **kwargs):
        """ This route is called when the host shows the current question's results.

        It's not a regular 'request.render' route because we handle the display of results using
        an AJAX request to be able to include the results in the currently displayed page. """

        survey = self._fetch_from_token(survey_token)

        if not survey or survey.session_state != 'in_progress':
            # no open session
            return False

        user_input_lines = request.env['survey.user_input.line'].search([
            ('survey_id', '=', survey.id),
            ('question_id', '=', survey.session_question_id.id),
            ('create_date', '>=', survey.session_start_time)
        ])

        return self._prepare_question_results_values(survey, user_input_lines)

    @http.route('/survey/session/leaderboard/<string:survey_token>', type='json', auth='user', website=True)
    def survey_session_leaderboard(self, survey_token, **kwargs):
        """ This route is called when the host shows the current question's attendees leaderboard.

        It's not a regular 'request.render' route because we handle the display of the leaderboard
        using an AJAX request to be able to include the results in the currently displayed page. """

        survey = self._fetch_from_token(survey_token)

        if not survey or survey.session_state != 'in_progress':
            # no open session
            return ''

        return request.env['ir.qweb']._render('survey.user_input_session_leaderboard', {
            'animate': True,
            'leaderboard': survey._prepare_leaderboard_values()
        })

    # ------------------------------------------------------------
    # QUICK ACCESS SURVEY ROUTES
    # ------------------------------------------------------------

    @http.route('/s', type='http', auth='public', website=True, sitemap=False)
    def survey_session_code(self, **post):
        """ Renders the survey session code page route.
        This page allows the user to enter the session code of the survey.
        It is mainly used to ease survey access for attendees in session mode. """
        return request.render("survey.survey_session_code")

    @http.route('/s/<string:session_code>', type='http', auth='public', website=True)
    def survey_start_short(self, session_code):
        """" Redirects to 'survey_start' route using a shortened link & token.
        Shows an error message if the survey is not valid.
        This route is used in survey sessions where we need short links for people to type. """
        survey, survey_error = self._fetch_from_session_code(session_code)

        if survey_error:
            return request.render('survey.survey_session_code',
                                  dict(**survey_error, session_code=session_code))
        return request.redirect(survey.get_start_url())

    @http.route('/survey/check_session_code/<string:session_code>', type='json', auth='public', website=True)
    def survey_check_session_code(self, session_code):
        """ Checks if the given code is matching a survey session_code.
        If yes, redirect to /s/code route.
        If not, return error. The user is invited to type again the code."""
        survey, survey_error = self._fetch_from_session_code(session_code)
        if survey_error:
            return survey_error
        return {'survey_url': survey.get_start_url()}

    def _prepare_manage_session_values(self, survey):
        is_first_question, is_last_question = False, False
        if survey.question_ids:
            most_voted_answers = survey._get_session_most_voted_answers()
            is_first_question = survey._is_first_page_or_question(survey.session_question_id)
            is_last_question = survey._is_last_page_or_question(most_voted_answers, survey.session_question_id)

        values = {
            'survey': survey,
            'is_last_question': is_last_question,
            'is_first_question': is_first_question,
            'is_session_closed': not survey.session_state,
        }

        values.update(self._prepare_question_results_values(survey, request.env['survey.user_input.line']))

        return values

    def _prepare_question_results_values(self, survey, user_input_lines):
        """ Prepares usefull values to display during the host session:

        - question_statistics_graph
          The graph data to display the bar chart for questions of type 'choice'
        - input_lines_values
          The answer values to text/date/datetime questions
        - answers_validity
          An array containing the is_correct value for all question answers.
          We need this special variable because of Chartjs data structure.
          The library determines the parameters (color/label/...) by only passing the answer 'index'
          (and not the id or anything else we can identify).
          In other words, we need to know if the answer at index 2 is correct or not.
        - answer_count
          The number of answers to the current question. """

        question = survey.session_question_id
        if not question:
            return {}
        answers_validity = []
        if (any(answer.is_correct for answer in question.suggested_answer_ids)):
            answers_validity = [answer.is_correct for answer in question.suggested_answer_ids]
            if question.comment_count_as_answer:
                answers_validity.append(False)

        full_statistics = question._prepare_statistics(user_input_lines)[0]
        input_line_values = []
        if question.question_type in ['char_box', 'date', 'datetime']:
            input_line_values = [{
                'id': line.id,
                'value': line['value_%s' % question.question_type]
            } for line in full_statistics.get('table_data', request.env['survey.user_input.line'])[:100]]

        return {
            'is_html_empty': is_html_empty,
            'question_statistics_graph': full_statistics.get('graph_data'),
            'input_line_values': input_line_values,
            'answers_validity': json.dumps(answers_validity),
            'answer_count': survey.session_question_answer_count,
            'attendees_count': survey.session_answer_count,
        }
