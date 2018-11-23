# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo.addons.survey.tests import common
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('functional')
class TestSurveyFlow(common.SurveyCase, HttpCase):

    def _access_start(self, survey):
        return self.url_open('/survey/start/%s' % survey.id)

    def _access_page(self, survey, token):
        return self.url_open('/survey/fill/%s/%s' % (survey.id, token))

    def _access_submit(self, survey, post_data):
        return self.url_open('/survey/submit/%s' % survey.id, data=post_data)

    def _find_csrf_token(self, text):
        csrf_token_re = re.compile("(input.+csrf_token.+value=\")([_a-zA-Z0-9]{51})", re.MULTILINE)
        return csrf_token_re.search(text).groups()[1]

    def _format_submission_data(self, page, answer_data, additional_post_data):
        post_data = {}
        post_data['page_id'] = page.id
        for question_id, answer_vals in answer_data.items():
            question = page.question_ids.filtered(lambda q: q.id == question_id)
            if question.question_type == 'multiple_choice':
                values = answer_vals['value']
                for value in values:
                    key = "%s_%s_%s_%s" % (page.survey_id.id, page.id, question.id, value)
                    post_data[key] = value
            else:
                [value] = answer_vals['value']
                key = "%s_%s_%s" % (page.survey_id.id, page.id, question.id)
                post_data[key] = value
        post_data.update(**additional_post_data)
        return post_data

    def test_flow_public(self):
        # Step: survey manager creates the survey
        # --------------------------------------------------
        with self.sudo(self.survey_manager):
            survey = self.env['survey.survey'].create({
                'title': 'Public Survey for Tarte Al Djotte',
                'auth_required': False,
            })

            # First page is about customer data
            page_0 = self.env['survey.page'].create({
                'title': 'Page1: Your Data',
                'survey_id': survey.id,
            })
            page0_q0 = self._add_question(
                page_0, 'What is your name', 'free_text',
                comments_allowed=False,
                constr_mandatory=True, constr_error_msg='Please enter your name')
            page0_q1 = self._add_question(
                page_0, 'What is your age', 'numerical_box',
                comments_allowed=False,
                constr_mandatory=True, constr_error_msg='Please enter your name')

            # Second page is about tarte al djotte
            page_1 = self.env['survey.page'].create({
                'title': 'Page2: Tarte Al Djotte',
                'survey_id': survey.id,
            })
            page1_q0 = self._add_question(
                page_1, 'What do you like most in our tarte al djotte', 'multiple_choice',
                labels=[{'value': 'The gras'},
                        {'value': 'The bette'},
                        {'value': 'The tout'},
                        {'value': 'The regime is fucked up'}])

        # fetch starting data to check only newly created data during this flow
        answers = self.env['survey.user_input'].search([('survey_id', '=', survey.id)])
        answer_lines = self.env['survey.user_input_line'].search([('survey_id', '=', survey.id)])
        self.assertEqual(answers, self.env['survey.user_input'])
        self.assertEqual(answer_lines, self.env['survey.user_input_line'])

        # Step: customer takes the survey
        # --------------------------------------------------

        # Customer opens start page
        r = self._access_start(survey)
        self.assertResponse(r, 200, [survey.title])

        # -> this should have generated a new answer with a token
        answers = self.env['survey.user_input'].search([('survey_id', '=', survey.id)])
        self.assertEqual(len(answers), 1)
        answer_token = answers.token
        self.assertTrue(answer_token)
        self.assertAnswer(answers, 'new', self.env['survey.page'])

        # Customer begins survey with first page
        r = self._access_page(survey, answer_token)
        self.assertResponse(r, 200)
        self.assertAnswer(answers, 'new', self.env['survey.page'])
        csrf_token = self._find_csrf_token(r.text)

        # Customer submit first page answers
        answer_data = {
            page0_q0.id: {'value': ['Alfred Poilvache']},
            page0_q1.id: {'value': [44.0]},
        }
        post_data = self._format_submission_data(page_0, answer_data, {'csrf_token': csrf_token, 'token': answer_token, 'button_submit': 'next'})
        r = self._access_submit(survey, post_data)
        self.assertResponse(r, 200)
        answers.invalidate_cache()  # TDE note: necessary as lots of sudo in controllers messing with cache

        # -> this should have generated answer lines
        self.assertAnswer(answers, 'skip', page_0)
        self.assertAnswerLines(page_0, answers, answer_data)

        # Customer is redirected on second page and begins filling it
        r = self._access_page(survey, answer_token)
        self.assertResponse(r, 200)
        csrf_token_re = re.compile("(input.+csrf_token.+value=\")([_a-zA-Z0-9]{51})", re.MULTILINE)
        csrf_token = csrf_token_re.search(r.text).groups()[1]

        # Customer submit second page answers
        answer_data = {
            page1_q0.id: {'value': [page1_q0.labels_ids.ids[0], page1_q0.labels_ids.ids[1]]},
        }
        post_data = self._format_submission_data(page_1, answer_data, {'csrf_token': csrf_token, 'token': answer_token, 'button_submit': 'next'})
        r = self._access_submit(survey, post_data)
        self.assertResponse(r, 200)
        answers.invalidate_cache()  # TDE note: necessary as lots of sudo in controllers messing with cache

        # -> this should have generated answer lines and closed the answer
        self.assertAnswer(answers, 'done', page_1)
        self.assertAnswerLines(page_1, answers, answer_data)
