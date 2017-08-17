# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestRecruitmentSurvey(common.SingleTransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestRecruitmentSurvey, cls).setUpClass()

        # Create some sample data to avoid demo data
        cls.department_admins = cls.env['hr.department'].create({'name': 'Admins'})
        cls.survey_sysadmin = cls.env['survey.survey'].create({'title': 'Questions for Sysadmin job offer'})

        cls.job_sysadmin = cls.env['hr.applicant'].create({
            'name': 'Technical worker',
            'department_id': cls.department_admins.id,
            'description': 'A nice Sys Admin job offer !'})
        cls.job_sysadmin.survey_id = cls.survey_sysadmin

    def test_start_survey(self):
        # We ensure that response is False because we don't know test order
        self.job_sysadmin.response_id = False
        action_start = self.job_sysadmin.action_start_survey()
        self.assertEqual(action_start['type'], 'ir.actions.act_url')
        self.assertNotEqual(self.job_sysadmin.response_id.id, False)
        self.assertIn(self.job_sysadmin.response_id.token, action_start['url'])
        action_start_with_response = self.job_sysadmin.action_start_survey()
        self.assertEqual(action_start_with_response, action_start)

    def test_print_survey(self):
        # We ensure that response is False because we don't know test order
        self.job_sysadmin.response_id = False
        action_print = self.job_sysadmin.action_print_survey()
        self.assertEqual(action_print['type'], 'ir.actions.act_url')
        self.job_sysadmin.response_id = self.env['survey.user_input'].create({'survey_id': self.survey_sysadmin.id})
        action_print_with_response = self.job_sysadmin.action_print_survey()
        self.assertIn(self.job_sysadmin.response_id.token, action_print_with_response['url'])
