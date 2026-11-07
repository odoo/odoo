# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr.tests.common import TestHrCommon
from odoo.tools.misc import file_open


class TestRecruitmentProcess(TestHrCommon):

    def test_00_recruitment_process(self):
        """ Test recruitment process """

        self.dep_rd = self.env['hr.department'].create({
            'name': 'Research & Development',
        })
        self.job_developer = self.env['hr.job'].create({
            'name': 'Experienced Developer',
            'department_id': self.dep_rd.id,
            'no_of_recruitment': 5,
        })
        self.employee_niv = self.env['hr.employee'].create({
            'name': 'Sharlene Rhodes',
        })
        self.job_developer = self.job_developer.with_user(self.res_users_hr_officer.id)
        self.employee_niv = self.employee_niv.with_user(self.res_users_hr_officer.id)

        # Create a new HR Recruitment Officer
        self.res_users_hr_recruitment_officer = self.env['res.users'].create({
            'company_id': self.env.ref('base.main_company').id,
            'name': 'HR Recruitment Officer',
            'login': "hrro",
            'email': "hrofcr@yourcompany.com",
            'groups_id': [(6, 0, [self.env.ref('hr_recruitment.group_hr_recruitment_user').id])]
        })

        # An applicant is interested in the job position. So he sends a resume by email.
        # In Order to test process of Recruitment so giving HR officer's rights
        with file_open('hr_recruitment/tests/resume.eml', 'rb') as request_file:
            request_message = request_file.read()
        self.env['mail.thread'].with_user(self.res_users_hr_recruitment_officer).message_process(
            'hr.applicant', request_message, custom_values={"job_id": self.job_developer.id})

        # After getting the mail, I check the details of the new applicant.
        applicant = self.env['hr.applicant'].search([('email_from', 'ilike', 'Richard_Anderson@yahoo.com')], limit=1)
        self.assertTrue(applicant, "Applicant is not created after getting the mail")
        resume_ids = self.env['ir.attachment'].search([
            ('name', '=', 'resume.pdf'),
            ('res_model', '=', self.env['hr.applicant']._name),
            ('res_id', '=', applicant.id)])
        self.assertEqual(applicant.name, 'Application for the post of Jr.application Programmer.', 'Applicant name does not match.')
        self.assertEqual(applicant.stage_id, self.env.ref('hr_recruitment.stage_job0'),
            "Stage should be 'New' and is '%s'." % (applicant.stage_id.name))
        self.assertTrue(resume_ids, 'Resume is not attached.')
        # I assign the Job position to the applicant
        applicant.write({'job_id': self.job_developer.id})
        # I schedule meeting with applicant for interview.
        applicant_meeting = applicant.action_makeMeeting()
        self.assertEqual(applicant_meeting['context']['default_name'], 'Application for the post of Jr.application Programmer.',
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
                "groups_id": [
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
            {"name": "Test Job Application for Notification", "job_id": job.id}
        )
        new_application_message = application.message_ids.filtered(
            lambda m: m.subtype_id == new_application_mt
        )
        self.assertTrue(
            user.partner_id in new_application_message.notified_partner_ids
        )

    def test_blacklist_providers(self):
        """Test blacklisting providers feature.
           In case the mail comes from the blacklisted mails list,
           we should not:
           - set the email_from to the newly created applicant
           - create an partner for the blaclisted mail and link it
                with the newly created applicant
        """
        self.env['ir.config_parameter'].set_param('hr_recruitment.blacklisted_emails',
                                                  'bla@com.com, mail-to-blacklist@gmail.com, bla1@odoo.com')
        applicant = self.env['hr.applicant'].message_new({
            'message_id': 'message_id_for_rec',
            'email_from': '"Mail to Blacklist Name" <mail-to-blacklist@gmail.com>',
            'from': '"Mail to Blacklist Name" <mail-to-blacklist@gmail.com>',
            'subject': 'CV',
            'body': 'I want to apply to your company',
        })
        self.assertFalse(applicant.email_from)
        self.assertFalse(applicant.partner_id)
