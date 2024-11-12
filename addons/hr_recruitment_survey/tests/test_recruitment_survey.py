# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import AccessError
from odoo.tests import common, Form, tagged
from odoo.tools import mute_logger


@tagged('security')
@tagged('at_install', '-post_install')  # LEGACY at_install
class TestRecruitmentSurvey(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestRecruitmentSurvey, cls).setUpClass()

        # Create users to test ACL
        cls.hr_recruitment_manager = mail_new_test_user(
            cls.env, name='Gustave Doré', login='hr_recruitment_manager', email='hr_recruitment.manager@example.com',
            groups='hr_recruitment.group_hr_recruitment_manager'
        )
        cls.hr_recruitment_user = mail_new_test_user(
            cls.env, name='Lukas Peeters', login='hr_recruitment_user', email='hr_recruitment.user@example.com',
            groups='hr_recruitment.group_hr_recruitment_user'
        )
        cls.hr_recruitment_interviewer = mail_new_test_user(
            cls.env, name='Eglantine Ask', login='hr_recruitment_interviewer', email='hr_recruitment.interviewer@example.com',
            groups='hr_recruitment.group_hr_recruitment_interviewer'
        )

        # Create some sample data to avoid demo data
        cls.department_admins = cls.env['hr.department'].create({'name': 'Admins'})

        cls.survey_sysadmin, cls.survey_developer, cls.survey_custom, cls.survey_restricted_1, cls.survey_restricted_2 = cls.env['survey.survey'].create([
            {'title': 'Questions for Sysadmin job offer', 'survey_type': 'recruitment'},
            {'title': 'Questions for Developer job offer', 'survey_type': 'recruitment'},
            {'title': 'Survey of type custom for security tests purpose', 'survey_type': 'custom'},
            {'title': 'Questions for restricted survey', 'survey_type': 'recruitment', 'restrict_user_ids': cls.hr_recruitment_manager.ids},
            {'title': 'Questions for restricted survey', 'survey_type': 'recruitment', 'restrict_user_ids': cls.hr_recruitment_user.ids},
        ])
        cls.question_ft = cls.env['survey.question'].create([
            {'title': 'Test Free Text', 'survey_id': cls.survey_sysadmin.id, 'sequence': 2, 'question_type': 'text_box'},
            {'title': 'Test Free Text', 'survey_id': cls.survey_developer.id, 'sequence': 2, 'question_type': 'text_box'},
            {'title': 'Test Free Text', 'survey_id': cls.survey_custom.id, 'sequence': 2, 'question_type': 'text_box'},
            {'title': 'Test Free Text', 'survey_id': cls.survey_restricted_1.id, 'sequence': 2, 'question_type': 'text_box'},
            {'title': 'Test Free Text', 'survey_id': cls.survey_restricted_2.id, 'sequence': 2, 'question_type': 'text_box'},
        ])

        # Jobs
        cls.job_sysadmin = cls.env['hr.job'].create({
            'name': 'System Admin',
            'survey_id': cls.survey_sysadmin.id,
            'description': None,
        })
        cls.job_developer = cls.env['hr.job'].create({
            'name': 'Developer',
            'survey_id': cls.survey_developer.id,
            'description': None,
        })
        cls.job_restricted_1 = cls.env['hr.job'].create({
            'name': 'Technical worker',
            'survey_id': cls.survey_restricted_1.id,
            'description': None,
        })
        cls.job_restricted_2 = cls.env['hr.job'].create({
            'name': 'Technical worker',
            'survey_id': cls.survey_restricted_2.id,
            'description': None,
        })

        # Applicants
        cls.job_applicant_sysadmin = cls.env['hr.applicant'].create({
            'partner_name': 'Jane Doe',
            'email_from': 'customer@example.com',
            'department_id': cls.department_admins.id,
            'job_id': cls.job_sysadmin.id,
        })
        cls.job_applicant_developer = cls.env['hr.applicant'].create({
            'partner_name': 'Jane Doe',
            'email_from': 'customer@example.com',
            'job_id': cls.job_developer.id,
        })
        cls.job_applicant_restricted_1 = cls.env['hr.applicant'].create({
            'partner_name': 'Jack',
            'email_from': 'jack@example.com',
            'job_id': cls.job_restricted_1.id,
        })
        cls.job_applicant_restricted_2 = cls.env['hr.applicant'].create({
            'partner_name': 'John',
            'email_from': 'john@example.com',
            'job_id': cls.job_restricted_2.id,
        })

    @mute_logger('odoo.addons.base.models.ir_access')
    def test_send_survey(self):
        Answer = self.env['survey.user_input']
        invite_recruitment = self._prepare_invite(self.survey_sysadmin, self.job_applicant_sysadmin)
        invite_recruitment.action_invite()

        self.assertEqual(invite_recruitment.applicant_ids, self.job_applicant_sysadmin)
        self.assertNotEqual(self.job_applicant_sysadmin.response_ids.ids, False)
        answers = Answer.search([('survey_id', '=', self.survey_sysadmin.id)])
        self.assertEqual(len(answers), 1)
        self.assertEqual(self.job_applicant_sysadmin.response_ids, answers)
        self.assertSetEqual(
            set(answers.mapped('email')),
            {self.job_applicant_sysadmin.email_from})

        # Tests ACL
        # Manager: ok for survey type recruitment
        invite_recruitment.with_user(self.hr_recruitment_manager).action_invite()
        with self.assertRaises(AccessError):
            self.survey_custom.with_user(self.hr_recruitment_manager).read(['title'])

        # Interviewer needs to be set as interviewer for the job or the applicant
        user = self.hr_recruitment_interviewer
        with self.subTest(user=user):
            with self.assertRaises(AccessError):
                invite_recruitment.with_user(user).action_invite()
            self.job_sysadmin.interviewer_ids = user
            invite_recruitment.with_user(user).action_invite()
            self.job_sysadmin.interviewer_ids = False
            with self.assertRaises(AccessError):
                invite_recruitment.with_user(user).action_invite()
            self.job_applicant_sysadmin.interviewer_ids = user
            invite_recruitment.with_user(user).action_invite()

        # Recruitment officer can send unrestricted surveys, or those restricted but allowing him.
        user = self.hr_recruitment_user
        with self.subTest(user=user):
            invite_recruitment.with_user(user).action_invite()
            invite_recruitment = self._prepare_invite(self.survey_restricted_1, self.job_applicant_restricted_1)
            with self.assertRaises(AccessError):
                invite_recruitment.with_user(user).action_invite()
            invite_recruitment = self._prepare_invite(self.survey_restricted_2, self.job_applicant_restricted_2)
            invite_recruitment.with_user(user).action_invite()

    @mute_logger('odoo.addons.base.models.ir_access')
    def test_print_survey(self):
        action_print = self.job_applicant_sysadmin.action_print_survey()
        self.assertEqual(action_print['type'], 'ir.actions.act_url')
        self.job_applicant_sysadmin.response_ids = self.env['survey.user_input'].create({'survey_id': self.survey_sysadmin.id})
        action_print_with_response = self.job_applicant_sysadmin.action_print_survey()
        self.assertIn(self.job_applicant_sysadmin.response_ids.access_token, action_print_with_response['url'])

        # Test ACL
        # Interviewer: no access to hr_applicant
        with self.assertRaises(AccessError):
            self.job_applicant_sysadmin.with_user(self.hr_recruitment_interviewer).action_print_survey()
        # Manager: ok for survey type recruitment
        self.job_applicant_sysadmin.with_user(self.hr_recruitment_manager).action_print_survey()
        with self.assertRaises(AccessError):
            self.survey_custom.with_user(self.hr_recruitment_manager).action_print_survey()
        # User: no access unless set as interviewer
        with self.assertRaises(AccessError):
            self.job_applicant_sysadmin.with_user(self.hr_recruitment_user).action_print_survey()
        self.job_applicant_sysadmin.interviewer_ids = self.hr_recruitment_user
        self.job_applicant_sysadmin.with_user(self.hr_recruitment_user).action_print_survey()

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_bulk_send_surveys(self):
        Answer = self.env['survey.user_input']

        applicants = self.job_applicant_sysadmin | self.job_applicant_developer

        # Prepare the wizard
        self.survey_sysadmin.write({'access_mode': 'public', 'users_login_required': False})
        self.survey_developer.write({'access_mode': 'public', 'users_login_required': False})

        invite_wizard = Form.from_action(self.env, applicants.action_send_survey()).save()

        # Send survey
        invite_wizard.action_invite()

        # Assert each applicant received a response
        for applicant in applicants:
            self.assertTrue(applicant.response_ids, f"No survey response found for {applicant.partner_name}")
            self.assertEqual(
                applicant.response_ids.survey_id,
                applicant.job_id.survey_id,
                f"Survey mismatch for {applicant.partner_name}"
            )
            self.assertIn(applicant.email_from, applicant.response_ids.mapped('email'))

        responses = Answer.search([('applicant_id', 'in', applicants.ids)])
        self.assertEqual(len(responses), 2, "Incorrect number of survey responses generated.")

    def _prepare_invite(self, survey, applicant):
        survey.write({'access_mode': 'public', 'users_login_required': False})
        return Form.from_action(self.env, applicant.action_send_survey()).save()
