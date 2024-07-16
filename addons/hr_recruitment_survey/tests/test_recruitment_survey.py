# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import AccessError
from odoo.tests import common, Form, tagged
from odoo.tools import mute_logger


@tagged('security')
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
        cls.survey_sysadmin, cls.survey_custom = cls.env['survey.survey'].create([
            {'title': 'Questions for Sysadmin job offer', 'survey_type': 'recruitment'},
            {'title': 'Survey of type custom for security tests purpose', 'survey_type': 'custom'}
        ])
        cls.question_ft = cls.env['survey.question'].create({
            'title': 'Test Free Text',
            'survey_id': cls.survey_sysadmin.id,
            'sequence': 2,
            'question_type': 'text_box',
        })
        cls.job = cls.env['hr.job'].create({
            'name': 'Technical worker',
            'survey_id': cls.survey_sysadmin.id,
            'description': None,
        })
        cls.job_applicant = cls.env['hr.applicant'].create({
            'candidate_id': cls.env['hr.candidate'].create({
                'partner_name': 'Jane Doe',
                'email_from': 'customer@example.com',
            }).id,
            'department_id': cls.department_admins.id,
            'description': 'A nice Sys Admin job offer!',
            'job_id': cls.job.id,
        })

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_send_survey(self):
        Answer = self.env['survey.user_input']
        invite_recruitment = self._prepare_invite(self.survey_sysadmin, self.job_applicant)
        invite_recruitment.action_invite()

        self.assertEqual(invite_recruitment.applicant_id, self.job_applicant)
        self.assertNotEqual(self.job_applicant.response_ids.ids, False)
        answers = Answer.search([('survey_id', '=', self.survey_sysadmin.id)])
        self.assertEqual(len(answers), 1)
        self.assertEqual(self.job_applicant.response_ids, answers)
        self.assertSetEqual(
            set(answers.mapped('email')),
            {self.job_applicant.email_from})

        # Tests ACL
        # Manager: ok for survey type recruitment
        invite_recruitment.with_user(self.hr_recruitment_manager).action_invite()
        with self.assertRaises(AccessError):
            self.survey_custom.with_user(self.hr_recruitment_manager).read(['title'])
        # Interviewer and User: need to be set as interviewer for the job or the applicant
        for user in (self.hr_recruitment_interviewer, self.hr_recruitment_user):
            with self.subTest(user=user):
                with self.assertRaises(AccessError):
                    invite_recruitment.with_user(user).action_invite()
                self.job.interviewer_ids = user
                invite_recruitment.with_user(user).action_invite()
                self.job.interviewer_ids = False
                with self.assertRaises(AccessError):
                    invite_recruitment.with_user(user).action_invite()
                self.job_applicant.interviewer_ids = user
                invite_recruitment.with_user(user).action_invite()

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_print_survey(self):
        action_print = self.job_applicant.action_print_survey()
        self.assertEqual(action_print['type'], 'ir.actions.act_url')
        self.job_applicant.response_ids = self.env['survey.user_input'].create({'survey_id': self.survey_sysadmin.id})
        action_print_with_response = self.job_applicant.action_print_survey()
        self.assertIn(self.job_applicant.response_ids.access_token, action_print_with_response['url'])

        # Test ACL
        # Interviewer: no access to hr_applicant
        with self.assertRaises(AccessError):
            self.job_applicant.with_user(self.hr_recruitment_interviewer).action_print_survey()
        # Manager: ok for survey type recruitment
        self.job_applicant.with_user(self.hr_recruitment_manager).action_print_survey()
        with self.assertRaises(AccessError):
            self.survey_custom.with_user(self.hr_recruitment_manager).action_print_survey()
        # User: no access unless set as interviewer
        with self.assertRaises(AccessError):
            self.job_applicant.with_user(self.hr_recruitment_user).action_print_survey()
        self.job_applicant.interviewer_ids = self.hr_recruitment_user
        self.job_applicant.with_user(self.hr_recruitment_user).action_print_survey()

    def _prepare_invite(self, survey, applicant):
        survey.write({
            'access_mode': 'public',
            'users_login_required': False})
        action = applicant.action_send_survey()
        invite_form = Form(self.env[action['res_model']].with_context(action['context']))
        return invite_form.save()
