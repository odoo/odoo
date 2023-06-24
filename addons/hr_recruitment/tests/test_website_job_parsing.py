# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr.tests.common import TestHrCommon
from odoo.modules.module import get_module_resource


class TestWebsiteJobParsing(TestHrCommon):
    """ Test recruitment process through job posting websites such as LinkedIn and ICTJobs """

    def test_00_linkedin_application_parsing(self):
        self.dep_rd = self.env['hr.department'].create({
            'name': 'Research & Development',
        })

        self.job_developer = self.env['hr.job'].create({
            'name': 'Experienced Developer',
            'department_id': self.dep_rd.id,
            'no_of_recruitment': 5
        })
        self.job_developer = self.job_developer.with_user(self.res_users_hr_officer.id)
        self.res_users_hr_recruitment_officer = self.env['res.users'].create({
            'company_id': self.env.ref('base.main_company').id,
            'name': 'HR Recruitment Officer',
            'login': "hrro",
            'email': "hrofcr@yourcompany.com",
            'groups_id': [(6, 0, [self.env.ref('hr_recruitment.group_hr_recruitment_user').id])]
        })
        # Application received through LinkedIn job offers
        with open(get_module_resource('hr_recruitment', 'tests', 'linkedin_offer.eml'), 'rb') as request_file:
            request_message = request_file.read()
            self.env['mail.thread'].with_user(self.res_users_hr_recruitment_officer).message_process(
                'hr.applicant', request_message, custom_values={"job_id": self.job_developer.id}
            )

        self.applicant = self.env['hr.applicant'].search([('job_id', '=', self.job_developer.id)])

        self.assertEqual(self.applicant.partner_name, "Richard Anderson")
        self.assertEqual(self.applicant.email_from, "")
        self.assertEqual(self.applicant.linkedin_profile, "https://www.PROFILEURLLINKEDIN.com")

    def test_01_ictjobs_application_parsing(self):
        self.dep_rd = self.env['hr.department'].create({
            'name': 'Research & Development',
        })
        self.job_developer = self.env['hr.job'].create({
            'name': 'Experienced Developer',
            'department_id': self.dep_rd.id,
            'no_of_recruitment': 5
        })
        self.job_developer = self.job_developer.with_user(self.res_users_hr_officer.id)
        self.res_users_hr_recruitment_officer = self.env['res.users'].create({
            'company_id': self.env.ref('base.main_company').id,
            'name': 'HR Recruitment Officer',
            'login': "hrro",
            'email': "hrofcr@yourcompany.com",
            'groups_id': [(6, 0, [self.env.ref('hr_recruitment.group_hr_recruitment_user').id])]
        })
        self.job_developer2 = self.env['hr.job'].create({
            'name': 'Junior Developer',
            'department_id': self.dep_rd.id,
            'no_of_recruitment': 5
        })
        # Application received through ICTJobs job offers
        with open(get_module_resource('hr_recruitment', 'tests', 'ictjobs_offer.eml'), 'rb') as request_file:
            request_message = request_file.read()
            self.env['mail.thread'].with_user(self.res_users_hr_recruitment_officer).message_process(
                'hr.applicant', request_message, custom_values={"job_id": self.job_developer2.id}
            )

        self.applicant2 = self.env['hr.applicant'].search([('job_id', '=', self.job_developer2.id)])
        self.assertEqual(self.applicant2.partner_name, "Richard Anderson")
        self.assertEqual(self.applicant2.email_from, "richard.anderson@gmail.com")
