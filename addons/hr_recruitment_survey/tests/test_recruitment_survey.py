# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, Form


class TestRecruitmentSurvey(common.SingleTransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestRecruitmentSurvey, cls).setUpClass()

        # Create some sample data to avoid demo data
        cls.department_admins = cls.env['hr.department'].create({'name': 'Admins'})
        cls.survey_sysadmin = cls.env['survey.survey'].create({'title': 'Questions for Sysadmin job offer'})

        # We need this, so that when we send survey, we don't get an error
        cls.question_ft = cls.env['survey.question'].create({
            'title': 'Test Free Text',
            'survey_id': cls.survey_sysadmin.id,
            'sequence': 2,
            'question_type': 'text_box',
        })

        cls.job = cls.env['hr.job'].create({
            'name': 'Technical worker',
            'survey_id': cls.survey_sysadmin.id,
        })
        cls.job_sysadmin = cls.env['hr.applicant'].create({
            'name': 'Technical worker',
            'partner_name': 'Jane Doe',
            'email_from': 'customer@example.com',
            'department_id': cls.department_admins.id,
            'description': 'A nice Sys Admin job offer !',
            'job_id': cls.job.id,
        })

    def test_send_survey(self):
        # We ensure that response is False because we don't know test order
        self.job_sysadmin.response_id = False
        Answer = self.env['survey.user_input']
        answers = Answer.search([('survey_id', '=', self.survey_sysadmin.id)])
        answers.unlink()

        self.survey_sysadmin.write({'access_mode': 'public', 'users_login_required': False})
        action = self.job_sysadmin.action_send_survey()

        invite_form = Form(self.env[action['res_model']].with_context({
            **action['context'],
        }))
        invite = invite_form.save()
        invite.action_invite()

        self.assertEqual(invite.applicant_id, self.job_sysadmin)
        self.assertNotEqual(self.job_sysadmin.response_id.id, False)
        answers = Answer.search([('survey_id', '=', self.survey_sysadmin.id)])
        self.assertEqual(len(answers), 1)
        self.assertEqual(self.job_sysadmin.response_id, answers)
        self.assertEqual(
            set(answers.mapped('email')),
            set([self.job_sysadmin.email_from]))

    def test_print_survey(self):
        # We ensure that response is False because we don't know test order
        self.job_sysadmin.response_id = False
        action_print = self.job_sysadmin.action_print_survey()
        self.assertEqual(action_print['type'], 'ir.actions.act_url')
        self.job_sysadmin.response_id = self.env['survey.user_input'].create({'survey_id': self.survey_sysadmin.id})
        action_print_with_response = self.job_sysadmin.action_print_survey()
        self.assertIn(self.job_sysadmin.response_id.access_token, action_print_with_response['url'])
