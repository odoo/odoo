# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from werkzeug.exceptions import NotFound
from werkzeug.urls import url_join

from odoo import http
from odoo.http import request


class UserInputSession(http.Controller):
    def _fetch_from_token(self, survey_token):
        """ Check that given survey_token matches a survey 'access_token'.
        Unlike the regular survey controller, user trying to access the survey must have full access rights! """
        return request.env['survey.survey'].search([('access_token', '=', survey_token)])

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
                'survey': survey,
                'survey_url': url_join(survey.get_base_url(), survey.get_start_short_url())
            })
        else:
            template_values = self._prepare_manage_session_values(survey)
            return request.render('survey.user_input_session_manage', template_values)

    @http.route('/survey/session/next_question/<string:survey_token>', type='json', auth='user', website=True)
    def survey_session_next_question(self, survey_token, **kwargs):
        """ This route is called when the host goes to the next question of the session.

        It's not a regular 'request.render' route because we handle the transition between
        questions using a AJAX call to be able to display a bioutiful fade in/out effect. """

        survey = self._fetch_from_token(survey_token)

        if not survey or not survey.session_state:
            # no open session
            return ''

        if survey.session_state == 'ready':
            survey._session_open()

        survey._session_trigger_next_question()
        template_values = self._prepare_manage_session_values(survey)
        template_values['is_rpc_call'] = True
        return request.env.ref('survey.user_input_session_manage_content').render(template_values)

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
            ('question_id', '=', survey.session_question_id.id)
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

        return request.env.ref('survey.user_input_session_leaderboard').render({
            'animate_width': True,
            'leaderboard': survey._prepare_leaderboard_values()
        })

    def _prepare_manage_session_values(self, survey):
        is_last_question = False
        if survey.question_ids:
            is_last_question = survey.session_question_id == survey.question_ids[-1]

        values = {
            'survey': survey,
            'is_last_question': is_last_question,
            'survey_url': url_join(survey.get_base_url(), survey.get_start_short_url()),
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
            'question_statistics_graph': full_statistics.get('graph_data'),
            'input_line_values': input_line_values,
            'answers_validity': json.dumps(answers_validity),
            'answer_count': survey.session_question_answer_count
        }
