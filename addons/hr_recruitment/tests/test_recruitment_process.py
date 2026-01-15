# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr.tests.common import TestHrCommon
from odoo.tools.misc import file_open


class TestRecruitmentProcess(TestHrCommon):

    def test_00_recruitment_process(self):
        """ Test recruitment process """

        dep_rd = self.env['hr.department'].create({
            'name': 'Research & Development',
        })
        job_developer = self.env['hr.job'].create({
            'name': 'Experienced Developer',
            'department_id': dep_rd.id,
            'no_of_recruitment': 5,
        })
        employee_niv = self.env['hr.employee'].create({
            'name': 'Sharlene Rhodes',
        })
        job_developer = job_developer.with_user(self.res_users_hr_officer.id)
        employee_niv = employee_niv.with_user(self.res_users_hr_officer.id)

        # Create a new HR Recruitment Officer
        res_users_hr_recruitment_officer = self.env['res.users'].create({
            'company_id': self.env.ref('base.main_company').id,
            'name': 'HR Recruitment Officer',
            'login': "hrro",
            'email': "hrofcr@yourcompany.com",
            'group_ids': [(6, 0, [self.env.ref('hr_recruitment.group_hr_recruitment_user').id])]
        })

        # An applicant is interested in the job position. So he sends a resume by email.
        # In Order to test process of Recruitment so giving HR officer's rights
        with file_open('hr_recruitment/tests/resume.eml', 'rb') as request_file:
            request_message = request_file.read()
        self.env['mail.thread'].with_user(res_users_hr_recruitment_officer).message_process(
            'hr.applicant', request_message, custom_values={"job_id": job_developer.id})

        # After getting the mail, I check the details of the new applicant.
        applicant = self.env['hr.applicant'].search([('email_from', 'ilike', 'Richard_Anderson@yahoo.com')], limit=1)
        self.assertTrue(applicant, "Applicant is not created after getting the mail")
        resume_ids = self.env['ir.attachment'].search([
            ('name', '=', 'resume.pdf'),
            ('res_model', '=', self.env['hr.applicant']._name),
            ('res_id', '=', applicant.id)])
        self.assertEqual(applicant.partner_name, 'Mr. Richard Anderson', 'Applicant name does not match.')
        self.assertEqual(applicant.stage_id, self.env.ref('hr_recruitment.stage_job0'),
            "Stage should be 'New' and is '%s'." % (applicant.stage_id.name))
        self.assertTrue(resume_ids, 'Resume is not attached.')
        # I assign the Job position to the applicant
        applicant.write({'job_id': job_developer.id})
        # I schedule meeting with applicant for interview.
        applicant_meeting = applicant.action_create_meeting()
        self.assertEqual(applicant_meeting['context']['default_name'], 'Mr. Richard Anderson',
            'Applicant name does not match.')

    def test_01_hr_application_notification(self):
        new_job_application_mt = self.env.ref(
            "hr_recruitment.mt_job_applicant_new"
        )
        new_application_mt = self.env.ref(
            "hr_recruitment.mt_applicant_new"
        )
        user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "user_1",
                "login": "user_1",
                "email": "user_1@example.com",
                "group_ids": [
                    (4, self.env.ref("hr.group_hr_manager").id),
                    (4, self.env.ref("hr_recruitment.group_hr_recruitment_manager").id),
                ],
            }
        )
        job = self.env["hr.job"].create({"name": "Test Job for Notification"})
        # Make test user follow Test HR Job
        self.env["mail.followers"].create(
            {
                "res_model": "hr.job",
                "res_id": job.id,
                "partner_id": user.partner_id.id,
                "subtype_ids": [(4, new_job_application_mt.id)],
            }
        )
        application = self.env["hr.applicant"].create(
            {"partner_name": "Test Job Application for Notification", "job_id": job.id}
        )
        new_application_message = application.message_ids.filtered(
            lambda m: m.subtype_id == new_application_mt
        )
        self.assertTrue(
            user.partner_id in new_application_message.notified_partner_ids
        )

    def test_job_platforms(self):
        self.env['hr.job.platform'].create({
            'name': 'YourJobPlatform',
            'email': 'yourjobplatform@platform.com',
            'regex': '^New application:.*from (.*)'
        })
        # Regex applied on Subject
        applicant = self.env['hr.applicant'].message_new({
            'message_id': 'message_id_for_rec',
            'email_from': '"Job Platform Application" <yourjobplatform@platform.com>',
            'from': '"Job Platform Application" <yourjobplatform@platform.com>',
            'subject': 'New application: ERP Implementation Consultant from John Doe',
            'body': 'I want to apply to your company',
        })

        # Regex applied on Body
        applicant2 = self.env['hr.applicant'].message_new({
            'message_id': 'message_id_for_rec',
            'email_from': '"Job Platform Application" <yourjobplatform@platform.com>',
            'from': '"Job Platform Application" <yourjobplatform@platform.com>',
            'subject': 'Very badly formatted subject :D',
            'body': 'New application: ERP Implementation Consultant from John Doe',
        })

        self.assertEqual(applicant.partner_name, 'John Doe')
        self.assertFalse(applicant.email_from)

        self.assertEqual(applicant2.partner_name, 'John Doe')
        self.assertFalse(applicant2.email_from)

    def test_email_application_multi_company(self):
        """ Make sure that receiving emails for jobs in companies different from self.env.company work. """
        other_company = self.env['res.company'].create({'name': 'Other Company'})
        job_developer = self.env['hr.job'].create({
            'name': 'Experienced Developer (Other Company)',
            'company_id': other_company.id,
        })

        with file_open('hr_recruitment/tests/resume.eml', 'rb') as request_file:
            request_message = request_file.read()
        self.env['mail.thread'].message_process('hr.applicant', request_message, custom_values={"job_id": job_developer.id})

        # Make sure the applicant are created in the right company
        applicant = self.env['hr.applicant'].search([('email_from', 'ilike', 'Richard_Anderson@yahoo.com')], limit=1)
        self.assertEqual(applicant.company_id, other_company, 'Applicant should be created in the right company')

    def test_email_application_department_with_no_company(self):
        """
        Test that applicants created from incoming emails are assigned the job's company when the job's department
        has no company set.
        """
        mystery_company = self.env["res.company"].create({"name": "Mystery Company"})
        _mail_alias_domain = self.env["mail.alias.domain"].create(
            {
                "company_ids": [(4, mystery_company.id)],
                "name": "test.example.com",
            }
        )
        alias = self.env["mail.alias"].create(
            {
                "alias_domain_id": mystery_company.alias_domain_id.id,
                "alias_name": "mystery_job",
                "alias_model_id": self.env["ir.model"]._get_id("hr.job"),
            }
        )

        mystery_department = self.env["hr.department"].create({"name": "Mystery Department", "company_id": False})
        mystery_job = self.env["hr.job"].create(
            {
                "name": "Mystery Job",
                "company_id": mystery_company.id,
                "department_id": mystery_department.id,
                "alias_id": alias.id,
            }
        )

        email = f"""MIME-Version: 1.0
Message-ID: <verymysteriousapplication>
From: Applicant <test@example.com>
To: {mystery_job.alias_id.display_name}
Subject: Job Application
Content-Type: text/plain; charset="UTF-8"

I want to work for you!"""

        applicant_from_email = self.env["mail.thread"].message_process("hr.applicant", email)
        applicant = self.env["hr.applicant"].browse(applicant_from_email)
        self.assertEqual(
            applicant.department_id, mystery_department, "Applicant should be assigned to the right department"
        )
        self.assertEqual(applicant.company_id, mystery_company, "Applicant should be created in the right company")
