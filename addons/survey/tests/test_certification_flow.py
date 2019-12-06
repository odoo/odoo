# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.base.models.ir_mail_server import IrMailServer
from odoo.addons.survey.tests import common
from odoo.tests import tagged


@tagged('-at_install', 'post_install', 'functional')
class TestCertificationFlow(common.TestSurveyCommonHttp):

    def setUp(self):
        super(TestCertificationFlow, self).setUp()

        with self.with_user('survey_manager'):
            self.certification = self.env['survey.survey'].create({
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

            self.q01 = self._add_question(
                'When do you know it\'s the right time to use the SO line model?', 'answer_selection',
                sequence=1, constr_mandatory=True, survey_id=self.certification.id,
                suggested_answers=[
                    {'value': 'Please stop'},
                    {'value': 'Only on the SO form'},
                    {'value': 'Only on the Survey form'},
                    {'value': 'Easy, all the time!!!', 'is_correct': True, 'answer_score': 2.0}
                ])

            self.q02 = self._add_question(
                'On average, how many lines of code do you need when you use SO line widgets?', 'answer_selection',
                sequence=2, constr_mandatory=True, survey_id=self.certification.id,
                suggested_answers=[
                    {'value': '1'},
                    {'value': '5', 'is_correct': True, 'answer_score': 2.0},
                    {'value': '100'},
                    {'value': '1000'}
                ])

            self.q03 = self._add_question(
                'What do you think about SO line widgets (not rated)?', 'text_box',
                sequence=3, constr_mandatory=True, constr_error_msg='Please tell us what you think', survey_id=self.certification.id)

            self.q04 = self._add_question(
                'On a scale of 1 to 10, how much do you like SO line widgets (not rated)?', 'answer_selection',
                sequence=4, constr_mandatory=True, survey_id=self.certification.id,
                suggested_answers=[
                    {'value': '-1'},
                    {'value': '0'},
                    {'value': '100'}
                ])

            self.q05 = self._add_question(
                'Select all the correct "types" of SO lines', 'answer_selection', selection_mode='multiple',
                sequence=5, constr_mandatory=False, survey_id=self.certification.id,
                suggested_answers=[
                    {'value': 'sale_order', 'is_correct': True, 'answer_score': 1.0},
                    {'value': 'survey_page', 'is_correct': True, 'answer_score': 1.0},
                    {'value': 'survey_question', 'is_correct': True, 'answer_score': 1.0},
                    {'value': 'a_future_and_yet_unknown_model', 'is_correct': True, 'answer_score': 1.0},
                    {'value': 'none', 'answer_score': -1.0}
                ])

    def test_flow_certification_employee(self):
        self.authenticate('user_emp', 'user_emp')

        # Employee opens start page
        response = self._access_start(self.certification)
        self.assertResponse(response, 200, [self.certification.title, 'Time limit for this survey', '10 minutes'])

        # -> this should have generated a new user_input with a token
        user_inputs = self.env['survey.user_input'].search([('survey_id', '=', self.certification.id)])
        self.assertEqual(len(user_inputs), 1)
        self.assertEqual(user_inputs.partner_id, self.user_emp.partner_id)
        answer_token = user_inputs.access_token

        # Employee begins survey with first page
        response, csrf_token = self._access_page(self.certification, answer_token)

        with patch.object(IrMailServer, 'connect'):
            self._answer_questions(self.q01, self.q01.suggested_answer_ids.ids[3], answer_token, csrf_token)
            self._access_page(self.certification, answer_token)
            self._answer_questions(self.q02, self.q02.suggested_answer_ids.ids[1], answer_token, csrf_token)
            self._access_page(self.certification, answer_token)
            self._answer_questions(self.q03, "I think they're great!", answer_token, csrf_token)
            self._access_page(self.certification, answer_token)
            self._answer_questions(self.q04, self.q04.suggested_answer_ids.ids[0], answer_token, csrf_token)
            self._access_page(self.certification, answer_token)
            self._answer_questions(self.q03, "Just kidding, I don't like it...", answer_token, csrf_token)
            self._access_page(self.certification, answer_token)
            self._answer_questions(self.q04, self.q04.suggested_answer_ids.ids[0], answer_token, csrf_token)
            self._access_page(self.certification, answer_token)
            self._answer_questions(self.q05, [self.q05.suggested_answer_ids.ids[0], self.q05.suggested_answer_ids.ids[1], self.q05.suggested_answer_ids.ids[3]], answer_token, csrf_token)
            self._access_page(self.certification, answer_token)

        user_inputs.invalidate_cache()
        # Check that certification is successfully passed
        self.assertEqual(user_inputs.scoring_percentage, 87.5)
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
