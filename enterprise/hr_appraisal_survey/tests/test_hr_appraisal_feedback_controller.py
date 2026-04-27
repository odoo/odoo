# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from freezegun import freeze_time

from odoo.addons.mail.tests.common import mail_new_test_user

from odoo.tests.common import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestHrAppraisalFeedbackController(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = mail_new_test_user(
            cls.env,
            name='Test Appraisal',
            login='TestAppraisal',
            email='test@test.com',
            groups='base.group_user',
        )

        cls.user_appraisal_officer = mail_new_test_user(
            cls.env,
            name='Appraisal Officer',
            login='AppraisalOfficer',
            email='appraisal_officer@test.com',
            groups='hr_appraisal.group_hr_appraisal_user',
        )

        cls.user_manager = mail_new_test_user(
            cls.env,
            name='User Manager',
            login='UserManager',
            email='user_manager@test.com',
        )

        cls.user_employee = cls.env['hr.employee'].create({
            'name': 'Me Myself and I',
            'user_id': cls.user.id
        })

        cls.appraisal_officer = cls.env['hr.employee'].create({
            'name': 'Mr. Appraisal Officer',
            'user_id': cls.user_appraisal_officer.id
        })

        cls.manager = cls.env['hr.employee'].create({
            'name': 'Mr. Manager',
            'user_id': cls.user_manager.id
        })

        cls.appraisal = cls.env['hr.appraisal'].create({
            'employee_id': cls.user_employee.id,
            'manager_ids': [cls.manager.id],
            'state': 'pending',
        })

        cls.appraisal_survey = cls.env['survey.survey'].create({
            'title': 'appraisal feedback',
            'questions_layout': 'one_page',
            'questions_selection': 'all',
            'access_mode': 'public',
            'survey_type': 'appraisal',
        })
        cls.question = cls.env['survey.question'].create({
            'survey_id': cls.appraisal_survey.id,
            'title': 'What is your name?',
            'sequence': 1,
            'question_type': 'char_box',
        })
        cls.survey_expired_text = "This survey is now closed. Thank you for your interest!"

    def test_appraisal_feedback_link_expiration(self):
        with freeze_time(datetime.date(2024, 9, 19)):
            feedback = self.env['appraisal.ask.feedback'].create({
                'appraisal_id': self.appraisal.id,
                'employee_ids': [self.user_employee.id],
                'deadline': datetime.date(2024, 9, 20),
                'survey_template_id': self.appraisal_survey.id,
            })
            feedback.action_send()
            answer = self.env['survey.user_input'].search([('appraisal_id', '=', self.appraisal.id)])
            url = answer.get_start_url()

            # link should be accessible before the deadline
            self.authenticate(self.user.login, self.user.login)
            res = self.url_open(url)
            self.assertTrue(self.survey_expired_text not in str(res.content), "The link should not be expired before the deadline")

            # link should be expired after the deadline
            with freeze_time(datetime.date(2024, 9, 21)):
                res = self.url_open(url)
                self.assertTrue(self.survey_expired_text in str(res.content), "The link should be expired after the deadline")

    def test_appraisal_feedback_link_for_managers(self):
        with freeze_time(datetime.date(2024, 9, 19)):
            feedback = self.env['appraisal.ask.feedback'].create({
                'appraisal_id': self.appraisal.id,
                'employee_ids': [self.user_employee.id],
                'deadline': datetime.date(2024, 9, 19),
                'survey_template_id': self.appraisal_survey.id,
            })
            feedback.action_send()
            answer = self.env['survey.user_input'].search([('appraisal_id', '=', self.appraisal.id)])
            char_answer = "John Doe"
            self.env['survey.user_input.line'].create({
                'survey_id': self.appraisal_survey.id,
                'user_input_id': answer.id,
                'question_id': self.question.id,
                'answer_type': 'numerical_box',
                'value_char_box': char_answer,
                'skipped': False,
            })
            url = answer.get_print_url()
            with freeze_time(datetime.date(2024, 9, 21)):
                self.authenticate(self.user_appraisal_officer.login, self.user_appraisal_officer.login)
                res = self.url_open(url)
                self.assertTrue(self.survey_expired_text not in str(res.content), "A user in Appraisal:Officer group should be able to access the survey answers after the deadline")
                self.assertTrue(char_answer in str(res.content), "A user in Appraisal:Officer group should be able to see the survey answers")

            with freeze_time(datetime.date(2024, 9, 21)):
                self.authenticate(self.user_manager.login, self.user_manager.login)
                res = self.url_open(url)
                self.assertTrue(self.survey_expired_text not in str(res.content), "The manager of an appraisal should be able to access the survey answers after the deadline")
                self.assertTrue(char_answer in str(res.content), "The manager of an appraisal should be able to see the survey answers")
