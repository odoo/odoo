# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

    def test_print_survey_access_mode_token(self):
        """Check that a survey with access_mode=token with questions defined can always be printed."""
        # Case: No questions, no answers -> general print informs the user "your survey is empty"
        survey = self.env['survey.survey'].with_user(self.survey_manager).create({
            'title': 'Test Survey without answers',
            'access_mode': 'token',
            'users_login_required': False,
            'users_can_go_back': False,
        })
        self.authenticate(self.survey_manager.login, self.survey_manager.login)
        response = self.url_open(f'/survey/print/{survey.access_token}')
        self.assertEqual(response.status_code, 200,
            "Print request to shall succeed for a survey without questions nor answers")
        self.assertIn("survey is empty", str(response.content),
            "Survey print without questions nor answers should inform user that the survey is empty")

        # Case: a question, no answers -> general print shows the question
        question = self.env['survey.question'].with_user(self.survey_manager).create({
            'title': 'Test Question',
            'survey_id': survey.id,
            'sequence': 1,
            'is_page': False,
            'question_type': 'char_box',
        })
        response = self.url_open(f'/survey/print/{survey.access_token}')
        self.assertEqual(response.status_code, 200,
            "Print request to shall succeed for a survey with questions but no answers")
        self.assertIn(question.title, str(response.content),
            "Should be possible to print a survey with a question and without answers")

        # Case: a question, an answers -> general print shows the question
        user_input = self._add_answer(survey, self.survey_manager.partner_id, state='done')
        self._add_answer_line(question, user_input, "Test Answer")
        response = self.url_open(f'/survey/print/{survey.access_token}')
        self.assertEqual(response.status_code, 200,
            "Print request without answer token, should be possible for a survey with questions and answers")
        self.assertIn(question.title, str(response.content),
            "Survey question should be visible in general print, even when answers exist and no answer_token is provided")
        self.assertNotIn("Test Answer", str(response.content),
            "Survey answer should not be in general print, when no answer_token is provided")

        # Case: a question, an answers -> print with answer_token shows both
        response = self.url_open(f'/survey/print/{survey.access_token}?answer_token={user_input.access_token}')
        self.assertEqual(response.status_code, 200,
            "Should be possible to print a sruvey with questions and answers")
        self.assertIn(question.title, str(response.content),
            "Question should appear when printing survey with using an answer_token")
        self.assertIn("Test Answer", str(response.content),
            "Answer should appear when printing survey with using an answer_token")
