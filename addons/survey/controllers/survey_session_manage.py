# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import json
import werkzeug

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
        """ Matches a survey against a passed session_code.
        We force the session_state to be reachable (ready / in_progress) to avoid people
        using this route to access other (private) surveys.
        We limit to sessions opened within the last 7 days to avoid potential abuses. """
        if session_code:
            matching_survey = request.env['survey.survey'].sudo().search([
                ('state', '=', 'open'),
                ('session_state', 'in', ['ready', 'in_progress']),
                ('session_start_time', '>', fields.Datetime.now() - relativedelta(days=7)),
                ('session_code', '=', session_code),
            ], limit=1)
            if matching_survey:
                return matching_survey

        return False

    # ------------------------------------------------------------
    # SURVEY SESSION MANAGEMENT
    # ------------------------------------------------------------

    @http.route('/survey/session/manage/<string:survey_token>', type='http', auth='user', website=True)
    def survey_session_manage(self, survey_token, **kwargs):
        """ Main route used by the host to 'manager' the session.
        - If the state of the session is 'ready'
          We render a template allowing the host to showcase the different options of the session
          and to actually start the session.
        - If the state of the session is 'in_progress'
          We render a template allowing the host to show the question results, display the attendees
          leaderboard or go to the next question of the session. """

        survey = self._fetch_from_token(survey_token)

        if not survey or not survey.session_state:
            # no open session
            return NotFound()

        if survey.session_state == 'ready':
            return request.render('survey.user_input_session_open', {
                'survey': survey
            })
        else:
            template_values = self._prepare_manage_session_values(survey)
            return request.render('survey.user_input_session_manage', template_values)

    @http.route('/survey/session/next_question/<string:survey_token>', type='json', auth='user', website=True)
    def survey_session_next_question(self, survey_token, **kwargs):
        """ This route is called when the host goes to the next question of the session.

        It's not a regular 'request.render' route because we handle the transition between
        questions using a AJAX call to be able to display a bioutiful fade in/out effect.

        It triggers the next question of the session.

        We artificially add 1 second to the 'current_question_start_time' to account for server delay.
        As the timing can influence the attendees score, we try to be fair with everyone by giving them
        an extra second before we start counting down.

        Frontend should take the delay into account by displaying the appropriate animations.

        Writing the next question on the survey is sudo'ed to avoid potential access right issues.
        e.g: a survey user can create a live session from any survey but he can only write
        on its own survey. """

        survey = self._fetch_from_token(survey_token)

        if not survey or not survey.session_state:
            # no open session
            return ''

        if survey.session_state == 'ready':
            survey._session_open()

        next_question = survey._get_session_next_question()

        # using datetime.datetime because we want the millis portion
        if next_question:
            now = datetime.datetime.now()
            survey.sudo().write({
                'session_question_id': next_question.id,
                'session_question_start_time': fields.Datetime.now() + relativedelta(seconds=1)
            })
            request.env['bus.bus'].sendone(survey.access_token, {
                'question_start': now.timestamp(),
                'type': 'next_question'
            })

            template_values = self._prepare_manage_session_values(survey)
            template_values['is_rpc_call'] = True
            return request.env.ref('survey.user_input_session_manage_content')._render(template_values)
        else:
            return False

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

        return request.env.ref('survey.user_input_session_leaderboard')._render({
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
        We match the session_code for open surveys.
        This route is used in survey sessions where we need short links for people to type. """

        survey = self._fetch_from_session_code(session_code)
        if survey:
            return werkzeug.utils.redirect("/survey/start/%s" % survey.access_token)

        return werkzeug.utils.redirect("/s")

    @http.route('/survey/check_session_code/<string:session_code>', type='json', auth='public', website=True)
    def survey_check_session_code(self, session_code):
        """ Checks if the given code is matching a survey session_code.
        If yes, redirect to /s/code route.
        If not, return error. The user is invited to type again the code. """
        survey = self._fetch_from_session_code(session_code)
        if survey:
            return {"survey_url": "/survey/start/%s" % survey.access_token}

        return {"error": "survey_wrong"}

    def _prepare_manage_session_values(self, survey):
        is_last_question = False
        if survey.question_ids:
            most_voted_answers = survey._get_session_most_voted_answers()
            is_last_question = survey._is_last_page_or_question(most_voted_answers, survey.session_question_id)

        values = {
            'survey': survey,
            'is_last_question': is_last_question,
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
