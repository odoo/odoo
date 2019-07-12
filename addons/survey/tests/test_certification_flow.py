# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.base.models.ir_mail_server import IrMailServer
from odoo.addons.survey.tests import common
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('functional')
class TestCertificationFlow(common.SurveyCase, HttpCase):
    def _answer_question(self, question, answer, answer_token, csrf_token, button_submit='next'):
        # Employee submits the question answer
        post_data = self._format_submission_data(question, answer, {'csrf_token': csrf_token, 'token': answer_token, 'button_submit': button_submit})
        response = self._access_submit(question.survey_id, answer_token, post_data)
        self.assertResponse(response, 200)

        # Employee is redirected on next question
        response = self._access_page(question.survey_id, answer_token)
        self.assertResponse(response, 200)

    def _format_submission_data(self, question, answer, additional_post_data):
        post_data = {}
        post_data['question_id'] = question.id
        if question.question_type == 'multiple_choice':
            values = answer
            for value in values:
                key = "%s_%s_%s" % (question.survey_id.id, question.id, value)
                post_data[key] = value
        else:
            key = "%s_%s" % (question.survey_id.id, question.id)
            post_data[key] = answer
        post_data.update(**additional_post_data)
        return post_data

    def test_flow_certificate(self):
        # Step: survey user creates the certification
        # --------------------------------------------------
        with self.with_user(self.survey_user):
            certification = self.env['survey.survey'].create({
                'title': 'User Certification for SO lines',
                'access_mode': 'public',
                'users_login_required': True,
                'questions_layout': 'page_per_question',
                'users_can_go_back': True,
                'scoring_type': 'scoring_with_answers',
                'passing_score': 85.0,
                'certificate': True,
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
                None, 'What do you think about SO line widgets (not rated)?', 'free_text',
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
        answer_token = user_inputs.token

        # Employee begins survey with first page
        response = self._access_page(certification, answer_token)
        self.assertResponse(response, 200)
        csrf_token = self._find_csrf_token(response.text)

        with patch.object(IrMailServer, 'connect'):
            self._answer_question(q01, q01.labels_ids.ids[3], answer_token, csrf_token)
            self._answer_question(q02, q02.labels_ids.ids[1], answer_token, csrf_token)
            self._answer_question(q03, "I think they're great!", answer_token, csrf_token)
            self._answer_question(q04, q04.labels_ids.ids[0], answer_token, csrf_token, button_submit='previous')
            self._answer_question(q03, "Just kidding, I don't like it...", answer_token, csrf_token)
            self._answer_question(q04, q04.labels_ids.ids[0], answer_token, csrf_token)
            self._answer_question(q05, [q05.labels_ids.ids[0], q05.labels_ids.ids[1], q05.labels_ids.ids[3]], answer_token, csrf_token)

        user_inputs.invalidate_cache()
        # Check that certification is successfully passed
        self.assertEqual(user_inputs.quizz_score, 87.5)
        self.assertTrue(user_inputs.quizz_passed)

        # Check answer correction is taken into account
        self.assertNotIn("I think they're great!", user_inputs.mapped('user_input_line_ids.value_free_text'))
        self.assertIn("Just kidding, I don't like it...", user_inputs.mapped('user_input_line_ids.value_free_text'))

        certification_email = self.env['mail.mail'].search([], limit=1, order="create_date desc")
        # Check certification email correctly sent and contains document
        self.assertIn("User Certification for SO lines", certification_email.subject)
        self.assertIn("employee@example.com", certification_email.email_to)
        self.assertEqual(len(certification_email.attachment_ids), 1)
        self.assertEqual(certification_email.attachment_ids[0].name, 'Certification Document.html')
