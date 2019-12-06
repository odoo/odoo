# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.survey.tests import common
from odoo.tests import tagged


@tagged('-at_install', 'post_install', 'functional')
class TestSurveyFlow(common.TestSurveyCommonHttp):

    def setUp(self):
        super(TestSurveyFlow, self).setUp()

        with self.with_user('survey_manager'):
            self.survey = self.env['survey.survey'].create({
                'title': 'Public Survey for Tarte Al Djotte',
                'access_mode': 'public',
                'users_login_required': False,
                'questions_layout': 'page_per_section',
                'state': 'open'
            })

            # First page is about customer data
            self.page_0 = self.env['survey.question'].create({
                'is_page': True,
                'sequence': 1,
                'title': 'Page1: Your Data',
                'survey_id': self.survey.id,
            })
            self.page0_q0 = self._add_question(
                'What is your name', 'text_box', page=self.page_0,
                comments_allowed=False, constr_mandatory=True, constr_error_msg='Please enter your name')
            self.page0_q1 = self._add_question(
                'What is your age', 'numerical_box', page=self.page_0,
                comments_allowed=False, constr_mandatory=True, constr_error_msg='Please enter your name')

            # Second page is about tarte al djotte
            self.page_1 = self.env['survey.question'].create({
                'is_page': True,
                'sequence': 4,
                'title': 'Page2: Tarte Al Djotte',
                'survey_id': self.survey.id,
            })
            self.page1_q0 = self._add_question(
                'What do you like most in our tarte al djotte', 'answer_selection', selection_mode='multiple', page=self.page_1,
                suggested_answers=[
                    {'value': 'The gras'}, {'value': 'The bette'},
                    {'value': 'The tout'}, {'value': 'The regime is fucked up'}
                ])

    def test_flow_public(self):
        # fetch starting data to check only newly created data during this flow
        user_input = self.env['survey.user_input'].search([('survey_id', '=', self.survey.id)])
        answer_lines = self.env['survey.user_input.line'].search([('survey_id', '=', self.survey.id)])
        self.assertEqual(user_input, self.env['survey.user_input'])
        self.assertEqual(answer_lines, self.env['survey.user_input.line'])

        # Step: customer takes the survey
        # --------------------------------------------------

        # Customer opens start page
        r = self._access_start(self.survey)
        self.assertResponse(r, 200, [self.survey.title])

        # -> this should have generated a new answer with a token
        user_input = self.env['survey.user_input'].search([('survey_id', '=', self.survey.id)])
        self.assertEqual(len(user_input), 1)
        answer_token = user_input.access_token
        self.assertTrue(answer_token)
        self.assertEqual(user_input.state, 'new')
        self.assertEqual(user_input.last_displayed_page_id, self.env['survey.question'])

        # Customer begins survey with first page
        response, csrf_token = self._access_page(self.survey, answer_token)
        self.assertResponse(response, 200)
        self.assertEqual(user_input.state, 'new')
        self.assertEqual(user_input.last_displayed_page_id, self.env['survey.question'])

        # Customer submit first page answers
        answer_data = {
            self.page0_q0: 'Alfred Poilvache',
            self.page0_q1: 44.0,
        }
        response = self._answer_questions(self.page0_q0 | self.page0_q1, answer_data, answer_token, csrf_token)
        user_input.invalidate_cache()
        # -> this should have generated answer lines
        self.assertEqual(user_input.state, 'skip')
        self.assertEqual(user_input.last_displayed_page_id, self.page_0)
        self.assertPageAnswered(self.page_0, user_input, answer_data)

        # Customer submit second page answers
        response, csrf_token = self._access_page(self.survey, answer_token)
        answer_data = {
            self.page1_q0: [self.page1_q0.suggested_answer_ids.ids[0], self.page1_q0.suggested_answer_ids.ids[1]],
        }
        response = self._answer_questions(self.page1_q0, answer_data, answer_token, csrf_token)
        user_input.invalidate_cache()
        # -> this should have generated answer lines and closed the answer
        self.assertEqual(user_input.state, 'done')
        self.assertEqual(user_input.last_displayed_page_id, self.page_1)
        self.assertPageAnswered(self.page_1, user_input, answer_data)
