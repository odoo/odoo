# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
          We render a template allowing the host to show the question results, display the attendee
          ranking or go to the next question of the session. """

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
        return request.env.ref('survey.user_input_session_manage_content').render(template_values).decode('UTF-8')

    @http.route('/survey/session/results/<string:survey_token>', type='json', auth='user', website=True)
    def survey_session_results(self, survey_token, **kwargs):
        """ This route is called when the host shows the current question's results.

        It's not a regular 'request.render' route because we handle the display of results using
        an AJAX request to be able to include the results in the currently displayed page. """

        survey = self._fetch_from_token(survey_token)

        if not survey or survey.session_state != 'in_progress':
            # no open session
            return ''

        user_input_lines = request.env['survey.user_input.line'].search([
            ('survey_id', '=', survey.id),
            ('question_id', '=', survey.session_question_id.id)
        ])
        question_statistics = survey.session_question_id._prepare_statistics(user_input_lines)[0]

        return request.env.ref('survey.survey_page_statistics_question').render({
            'page_record_limit': 10,
            'hide_question_title': True,
            'no_print_url': True,
            'survey': survey,
            'question': survey.session_question_id,
            'question_data': question_statistics,
        }).decode('UTF-8')

    @http.route('/survey/session/ranking/<string:survey_token>', type='json', auth='user', website=True)
    def survey_session_ranking(self, survey_token, **kwargs):
        """ This route is called when the host shows the current question's attendees ranking.

        It's not a regular 'request.render' route because we handle the display of the ranking
        using an AJAX request to be able to include the results in the currently displayed page. """

        survey = self._fetch_from_token(survey_token)

        if not survey or survey.session_state != 'in_progress':
            # no open session
            return ''

        return request.env.ref('survey.user_input_session_ranking').render({
            'animate_width': True,
            'ranking': survey._prepare_ranking_values()
        }).decode('UTF-8')

    def _prepare_manage_session_values(self, survey):
        is_last_question = False
        if survey.question_ids:
            is_last_question = survey.session_question_id == survey.question_ids[-1]

        return {
            'survey': survey,
            'is_last_question': is_last_question,
            'survey_url': url_join(survey.get_base_url(), survey.get_start_short_url()),
        }
