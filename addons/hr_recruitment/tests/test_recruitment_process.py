# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
from odoo.addons.hr.tests.common import TestHrCommon
from odoo.modules.module import get_module_resource


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
        with open(get_module_resource('hr_recruitment', 'tests', 'resume.eml'), 'rb') as request_file:
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
        self.assertEqual(applicant.stage_id, self.env.ref('hr_recruitment.stage_job1'),
            "Stage should be 'Initial qualification' and is '%s'." % (applicant.stage_id.name))
        self.assertTrue(resume_ids, 'Resume is not attached.')
        # I assign the Job position to the applicant
        applicant.write({'job_id': self.job_developer.id})
        # I schedule meeting with applicant for interview.
        applicant_meeting = applicant.action_makeMeeting()
        self.assertEqual(applicant_meeting['context']['default_name'], 'Application for the post of Jr.application Programmer.',
            'Applicant name does not match.')
