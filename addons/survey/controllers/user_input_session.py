# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug
from werkzeug.urls import url_join

from odoo import _, http
from odoo.http import request


class UserInputSession(http.Controller):
    def _fetch_from_access_token(self, survey_token):
        """ Check that given survey_token matches a survey 'access_token'.
        Returns a sudo-ed browse record of survey in order to avoid access rights
        issues now that access is granted through token. """
        survey_sudo = request.env['survey.survey'].with_context(active_test=False).sudo().search([('access_token', '=', survey_token)])
        return survey_sudo

    @http.route('/survey/session_manage/<string:survey_token>', type='http', auth='user', website=True)
    def survey_session_manage(self, survey_token, **kwargs):
        """ Main route used by the host to 'manager' the session.
        - If the state of the session is 'ready'
          We render a template allowing the host to showcase the different options of the session
          and to actually start the session.
        - If the state of the session is 'in_progress'
          We render a template allowing the host to show the question results, display the attendee
          ranking or go to the next question of the session. """

        survey_sudo = self._fetch_from_access_token(survey_token)
        current_session = survey_sudo.user_input_current_session

        if not current_session:
            # no open session
            return werkzeug.utils.redirect('/')

        if current_session.state == 'ready':
            base_url = request.env['ir.config_parameter'].sudo().get_param("web.base.url")
            return request.render('survey.user_input_session_open', {
                'session': current_session,
                'survey': survey_sudo,
                'survey_url': url_join(base_url, survey_sudo.get_start_url())
            })
        else:
            template_values = self._prepare_manage_session_values(survey_sudo, current_session)
            return request.render('survey.user_input_session_manage', template_values)

    @http.route('/survey/session_next_question/<string:survey_token>', type='json', auth='user', website=True)
    def survey_session_next_question(self, survey_token, **kwargs):
        """ This route is called when the host goes to the next question of the session.

        It's not a regular 'request.render' route because we handle the transition between
        questions using a AJAX call to be able to display a bioutiful fade in/out effect. """

        survey_sudo = self._fetch_from_access_token(survey_token)
        current_session = survey_sudo.user_input_current_session

        if not current_session:
            # no open session
            return werkzeug.utils.redirect('/')

        if current_session.state == 'ready':
            current_session.write({'state': 'in_progress'})
            current_session.flush(['state'])

        current_session.next_question()
        template_values = self._prepare_manage_session_values(survey_sudo, current_session)
        template_values['is_transitioned'] = True
        return request.env.ref('survey.user_input_session_manage_content').render(template_values).decode('UTF-8')

    @http.route('/survey/session_results/<string:survey_token>', type='json', auth='user', website=True)
    def survey_session_results(self, survey_token, **kwargs):
        """ This route is called when the host shows the current question's results.

        It's not a regular 'request.render' route because we handle the display of results using
        an AJAX request to be able to include the results in the currently displayed page. """

        survey_sudo = self._fetch_from_access_token(survey_token)
        current_session = survey_sudo.user_input_current_session

        if not current_session:
            # no open session
            return werkzeug.utils.redirect('/')

        user_input_lines = request.env['survey.user_input.line'].search([
            ('user_input_id', 'in', current_session.answer_ids.ids),
            ('question_id', '=', current_session.current_question_id.id)
        ])
        questions_statistics = current_session.current_question_id._prepare_statistics(user_input_lines)[0]

        return request.env.ref('survey.survey_page_statistics_question').render({
            'page_record_limit': 10,
            'hide_question_title': True,
            'survey': survey_sudo,
            'session': current_session,
            'question': current_session.current_question_id,
            'question_data': questions_statistics
        }).decode('UTF-8')

    @http.route('/survey/session_ranking/<string:survey_token>', type='json', auth='user', website=True)
    def survey_session_ranking(self, survey_token, **kwargs):
        """ This route is called when the host shows the current question's attendees ranking.

        It's not a regular 'request.render' route because we handle the display of the ranking
        using an AJAX request to be able to include the results in the currently displayed page. """

        survey_sudo = self._fetch_from_access_token(survey_token)
        current_session = survey_sudo.user_input_current_session

        if not current_session:
            # no open session
            return werkzeug.utils.redirect('/')

        return request.env.ref('survey.user_input_session_ranking').render({
            'ranking': current_session._prepare_ranking_values()
        }).decode('UTF-8')

    def _prepare_manage_session_values(self, survey, session):
        question_ids = list(enumerate(survey.question_ids))
        current_question_index = question_ids.index(
            next(question for question in question_ids if question[1] == session.current_question_id)
        )

        vals = {
            'session': session,
            'answer': request.env['survey.user_input'],
            'survey': survey,
            'is_last_question': current_question_index == (len(survey.question_ids) - 1),
        }

        return vals
