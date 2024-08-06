# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.base.models.ir_mail_server import IrMailServer
from odoo.addons.survey.tests import common
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('-at_install', 'post_install', 'functional')
class TestCertificationFlow(common.TestSurveyCommon, HttpCase):

    def test_flow_certification(self):
        # Step: survey user creates the certification
        # --------------------------------------------------
        with self.with_user('survey_user'):
            certification = self.env['survey.survey'].create({
                'title': 'User Certification for SO lines',
                'access_mode': 'public',
                'users_login_required': True,
                'questions_layout': 'page_per_question',
                'users_can_go_back': True,
                'scoring_type': 'scoring_with_answers',
                'scoring_success_min': 85.0,
                'certification': True,
                'certification_mail_template_id': self.env.ref('survey.mail_template_certification').id,
                'is_time_limited': True,
                'time_limit': 10,
                'state': 'open',
            })

            q01 = self._add_question(
                None, 'When do you know it\'s the right time to use the SO line model?', 'simple_choice',
                sequence=1,
                constr_mandatory=True, constr_error_msg='Please select an answer', survey_id=certification.id,
                labels=[
                    {'value': 'Please stop'},
                    {'value': 'Only on the SO form'},
                    {'value': 'Only on the Survey form'},
                    {'value': 'Easy, all the time!!!', 'is_correct': True, 'answer_score': 2.0}
                ])

            q02 = self._add_question(
                None, 'On average, how many lines of code do you need when you use SO line widgets?', 'simple_choice',
                sequence=2,
                constr_mandatory=True, constr_error_msg='Please select an answer', survey_id=certification.id,
                labels=[
                    {'value': '1'},
                    {'value': '5', 'is_correct': True, 'answer_score': 2.0},
                    {'value': '100'},
                    {'value': '1000'}
                ])

            q03 = self._add_question(
                None, 'What do you think about SO line widgets (not rated)?', 'text_box',
                sequence=3,
                constr_mandatory=True, constr_error_msg='Please tell us what you think', survey_id=certification.id)

            q04 = self._add_question(
                None, 'On a scale of 1 to 10, how much do you like SO line widgets (not rated)?', 'simple_choice',
                sequence=4,
                constr_mandatory=True, constr_error_msg='Please tell us what you think', survey_id=certification.id,
                labels=[
                    {'value': '-1'},
                    {'value': '0'},
                    {'value': '100'}
                ])

            q05 = self._add_question(
                None, 'Select all the correct "types" of SO lines', 'multiple_choice',
                sequence=5,
                constr_mandatory=False, survey_id=certification.id,
                labels=[
                    {'value': 'sale_order', 'is_correct': True, 'answer_score': 1.0},
                    {'value': 'survey_page', 'is_correct': True, 'answer_score': 1.0},
                    {'value': 'survey_question', 'is_correct': True, 'answer_score': 1.0},
                    {'value': 'a_future_and_yet_unknown_model', 'is_correct': True, 'answer_score': 1.0},
                    {'value': 'none', 'answer_score': -1.0}
                ])

        # Step: employee takes the certification
        # --------------------------------------------------
        self.authenticate('user_emp', 'user_emp')

        # Employee opens start page
        response = self._access_start(certification)
        self.assertResponse(response, 200, [certification.title, 'Time limit for this survey', '10 minutes'])

        # -> this should have generated a new user_input with a token
        user_inputs = self.env['survey.user_input'].search([('survey_id', '=', certification.id)])
        self.assertEqual(len(user_inputs), 1)
        self.assertEqual(user_inputs.partner_id, self.user_emp.partner_id)
        answer_token = user_inputs.access_token

        # Employee begins survey with first page
        response = self._access_page(certification, answer_token)
        self.assertResponse(response, 200)
        csrf_token = self._find_csrf_token(response.text)

        r = self._access_begin(certification, answer_token)
        self.assertResponse(r, 200)

        with patch.object(IrMailServer, 'connect'):
            self._answer_question(q01, q01.suggested_answer_ids.ids[3], answer_token, csrf_token)
            self._answer_question(q02, q02.suggested_answer_ids.ids[1], answer_token, csrf_token)
            self._answer_question(q03, "I think they're great!", answer_token, csrf_token)
            self._answer_question(q04, q04.suggested_answer_ids.ids[0], answer_token, csrf_token, button_submit='previous')
            self._answer_question(q03, "Just kidding, I don't like it...", answer_token, csrf_token)
            self._answer_question(q04, q04.suggested_answer_ids.ids[0], answer_token, csrf_token)
            self._answer_question(q05, [q05.suggested_answer_ids.ids[0], q05.suggested_answer_ids.ids[1], q05.suggested_answer_ids.ids[3]], answer_token, csrf_token)

        user_inputs.invalidate_cache()
        # Check that certification is successfully passed
        self.assertEqual(user_inputs.scoring_percentage, 87.5)
        self.assertTrue(user_inputs.scoring_success)

        # Check that the certification is still successful even if scoring_success_min of certification is modified
        certification.write({'scoring_success_min': 90})
        self.assertTrue(user_inputs.scoring_success)

        # Check answer correction is taken into account
        self.assertNotIn("I think they're great!", user_inputs.mapped('user_input_line_ids.value_text_box'))
        self.assertIn("Just kidding, I don't like it...", user_inputs.mapped('user_input_line_ids.value_text_box'))

        certification_email = self.env['mail.mail'].sudo().search([], limit=1, order="create_date desc")
        # Check certification email correctly sent and contains document
        self.assertIn("User Certification for SO lines", certification_email.subject)
        self.assertIn("employee@example.com", certification_email.email_to)
        self.assertEqual(len(certification_email.attachment_ids), 1)
        self.assertEqual(certification_email.attachment_ids[0].name, 'Certification Document.html')

    def test_randomized_certification(self):
        # Step: survey user creates the randomized certification
        # --------------------------------------------------
        with self.with_user('survey_user'):
            certification = self.env['survey.survey'].create({
                'title': 'User randomized Certification',
                'questions_layout': 'page_per_section',
                'questions_selection': 'random',
                'state': 'open',
                'scoring_type': 'scoring_without_answers',
            })

            page1 = self._add_question(
                None, 'Page 1', None,
                sequence=1,
                survey_id=certification.id,
                is_page=True,
                random_questions_count=1,
            )

            q101 = self._add_question(
                None, 'What is the answer to the first question?', 'simple_choice',
                sequence=2,
                constr_mandatory=True, constr_error_msg='Please select an answer', survey_id=certification.id,
                labels=[
                    {'value': 'The correct answer', 'is_correct': True, 'answer_score': 1.0},
                    {'value': 'The wrong answer'},
                ])

            q102 = self._add_question(
                None, 'What is the answer to the second question?', 'simple_choice',
                sequence=3,
                constr_mandatory=True, constr_error_msg='Please select an answer', survey_id=certification.id,
                labels=[
                    {'value': 'The correct answer', 'is_correct': True, 'answer_score': 1.0},
                    {'value': 'The wrong answer'},
                ])

        # Step: employee takes the randomized certification
        # --------------------------------------------------
        self.authenticate('user_emp', 'user_emp')

        # Employee opens start page
        response = self._access_start(certification)

        # -> this should have generated a new user_input with a token
        user_inputs = self.env['survey.user_input'].search([('survey_id', '=', certification.id)])
        self.assertEqual(len(user_inputs), 1)
        self.assertEqual(user_inputs.partner_id, self.user_emp.partner_id)
        answer_token = user_inputs.access_token

        # Employee begins survey with first page
        response = self._access_page(certification, answer_token)
        self.assertResponse(response, 200)
        csrf_token = self._find_csrf_token(response.text)

        r = self._access_begin(certification, answer_token)
        self.assertResponse(r, 200)

        with patch.object(IrMailServer, 'connect'):
            question_ids = user_inputs.predefined_question_ids
            self.assertEqual(len(question_ids), 1, 'Only one question should have been selected by the randomization')
            # Whatever which question was selected, the correct answer is the first one
            self._answer_question(question_ids, question_ids.suggested_answer_ids.ids[0], answer_token, csrf_token)

        statistics = user_inputs._prepare_statistics()
        self.assertEqual(statistics, [[
            {'text': 'Correct', 'count': 1},
            {'text': 'Partially', 'count': 0},
            {'text': 'Incorrect', 'count': 0},
            {'text': 'Unanswered', 'count': 0},
        ]], "With the configured randomization, there should be exactly 1 correctly answered question and none skipped.")
