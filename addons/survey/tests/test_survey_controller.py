# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import Command
from odoo.addons.survey.tests import common
from odoo.tests.common import HttpCase


class TestSurveyController(common.TestSurveyCommon, HttpCase):

    def test_submit_route_scoring_after_page(self):
        """ Check that the submit route for a scoring after page survey is returning the
        accurate correct answers depending on the survey layout and the active page questions.
        The correct answers of the inactive conditional questions shouldn't be returned.
        """
        survey = self.env['survey.survey'].create({
            'title': 'How much do you know about words?',
            'scoring_type': 'scoring_with_answers_after_page',
        })
        (
            a_q1_partial, a_q1_correct, a_q1_incorrect,
            a_q2_incorrect, a_q2_correct,
            a_q3_correct, a_q3_incorrect
        ) = self.env['survey.question.answer'].create([
            {'value': 'A thing full of letters.', 'answer_score': 1.0},
            {'value': 'A unit of language, [...], carrying a meaning.', 'answer_score': 4.0, 'is_correct': True},
            {'value': 'A thing related to space', 'answer_score': -4.0},
            {'value': 'Yes', 'answer_score': -0.5},
            {'value': 'No', 'answer_score': 0.5, 'is_correct': True},
            {'value': 'Yes', 'answer_score': 0.5, 'is_correct': True},
            {'value': 'No', 'answer_score': 0.2},
        ])
        q1, q2, q3 = self.env['survey.question'].create([{
            'survey_id': survey.id,
            'title': 'What is a word?',
            'sequence': 2,
            'question_type': 'simple_choice',
            'suggested_answer_ids': [Command.set((a_q1_partial | a_q1_correct | a_q1_incorrect).ids)],
            'constr_mandatory': False,
        }, {
            'survey_id': survey.id,
            'title': 'Are you sure?',
            'sequence': 3,
            'question_type': 'simple_choice',
            'suggested_answer_ids': [Command.set((a_q2_incorrect | a_q2_correct).ids)],
            'triggering_answer_ids': [Command.set((a_q1_partial | a_q1_incorrect).ids)],
            'constr_mandatory': False,
        }, {
            'survey_id': survey.id,
            'title': 'Are you sure?',
            'sequence': 5,
            'question_type': 'simple_choice',
            'suggested_answer_ids': [Command.set((a_q3_correct | a_q3_incorrect).ids)],
            'triggering_answer_ids': [Command.set([a_q1_correct.id])],
            'constr_mandatory': False,
        }])
        pages = [
            {'is_page': True, 'question_type': False, 'sequence': 1, 'title': 'Page 0', 'survey_id': survey.id},
            {'is_page': True, 'question_type': False, 'sequence': 4, 'title': 'Page 1', 'survey_id': survey.id},
        ]

        q1_correct_answer = {str(q1.id): [a_q1_correct.id]}
        cases = [
            ('page_per_question', [], q1_correct_answer),
            ('page_per_question', a_q1_correct, q1_correct_answer),
            ('page_per_question', a_q1_incorrect, q1_correct_answer),
            ('one_page', [], q1_correct_answer), # skipping gives answers for active questions (q2 and q3 conditional questions are inactive)
            ('one_page', a_q1_correct, {**q1_correct_answer, str(q3.id): [a_q3_correct.id]}),
            ('one_page', a_q1_partial, {**q1_correct_answer, str(q2.id): [a_q2_correct.id]}),
            # page0 contains q1 and q2, page1 contains q3
            ('page_per_section', [], q1_correct_answer),
            ('page_per_section', a_q1_correct, q1_correct_answer), # no correct answers for q3 because q3 is not on the same page as q1
            ('page_per_section', a_q1_partial, {**q1_correct_answer, str(q2.id): [a_q2_correct.id]}),
        ]

        for case_index, (layout, answer_q1, expected_correct_answers) in enumerate(cases):
            with self.subTest(case_index=case_index, layout=layout):
                survey.questions_layout = layout
                if layout == 'page_per_section':
                    page0, _ = self.env['survey.question'].create(pages)

                response = self._access_start(survey)
                user_input = self.env['survey.user_input'].search([('access_token', '=', response.url.split('/')[-1])])
                answer_token = user_input.access_token

                r = self._access_page(survey, answer_token)
                self.assertResponse(r, 200)
                csrf_token = self._find_csrf_token(response.text)

                r = self._access_begin(survey, answer_token)
                self.assertResponse(r, 200)

                post_data = {'csrf_token': csrf_token, 'token': answer_token}
                post_data[q1.id] = answer_q1.id if answer_q1 else answer_q1
                if layout == 'page_per_question':
                    post_data['question_id'] = q1.id
                elif layout == 'page_per_section':
                    post_data['page_id'] = page0.id

                # Submit answers and check the submit route is returning the accurate correct answers
                response = self._access_submit(survey, answer_token, post_data)
                self.assertResponse(response, 200)
                self.assertEqual(response.json()['result'][0], expected_correct_answers)

                user_input.invalidate_recordset() # TDE note: necessary as lots of sudo in controllers messing with cache

    def test_live_session_without_question(self):
        """Test that the live session ('Thank You' page) does not crash when no question is present."""
        survey = self.env['survey.survey'].with_user(self.survey_manager).create({
            'title': 'Live Session Survey',
            'access_mode': 'token',
            'users_login_required': False,
            'session_question_start_time': datetime.datetime(2023, 7, 7, 12, 0, 0),
        })

        self.authenticate(self.survey_manager.login, self.survey_manager.login)

        # Call the url without any question
        session_manage_url = f'/survey/session/manage/{survey.access_token}'
        response = self.url_open(session_manage_url)
        self.assertEqual(response.status_code, 200, "Should be able to open live session manage page")
