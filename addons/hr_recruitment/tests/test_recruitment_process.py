# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
from odoo.modules.module import get_module_resource


class TestRecruitmentProcess(common.TransactionCase):

    def test_00_recruitment_process(self):
        """ Test recruitment process """

        # adding custom fields, so I can later check that they are populated when converting applicant to employee
        self.create_field('hr.applicant', 'x_hobby')
        self.create_field('hr.applicant', 'x_bff')
        self.create_field('hr.employee',  'x_hobby')
        self.create_field('hr.employee',  'x_bff')
        self.create_field('hr.employee',  'x_something_we_dont_ask_applicants')

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
            'hr.applicant', request_message, custom_values={"job_id": self.env.ref('hr.job_developer').id})

        # After getting the mail, I check the details of the new applicant.
        applicant = self.env['hr.applicant'].search([('email_from', 'ilike', 'Richard_Anderson@yahoo.com')], limit=1)
        self.assertTrue(applicant, "Applicant is not created after getting the mail")
        resume_ids = self.env['ir.attachment'].search([
            ('name', '=', 'resume.pdf'),
            ('res_model', '=', self.env['hr.applicant']._name),
            ('res_id', '=', applicant.id)])
        self.assertEquals(applicant.name, 'Application for the post of Jr.application Programmer.', 'Applicant name does not match.')
        self.assertEquals(applicant.stage_id, self.env.ref('hr_recruitment.stage_job1'),
            "Stage should be 'Initial qualification' and is '%s'." % (applicant.stage_id.name))
        self.assertTrue(resume_ids, 'Resume is not attached.')
        # I assign the Job position to the applicant
        applicant.write({'job_id': self.env.ref('hr.job_developer').id})
        # I schedule meeting with applicant for interview.
        applicant_meeting = applicant.action_makeMeeting()
        self.assertEquals(applicant_meeting['context']['default_name'], 'Application for the post of Jr.application Programmer.',
            'Applicant name does not match.')

        # 'Manually' set some applicant fields
        applicant.x_hobby = 'Knitting'
        applicant.x_bff = 'Mr. Bob'

        # Hire the applicant - make him an employee!
        applicant.create_employee_from_applicant()
        employee = self.env['hr.employee'].search([('name', 'ilike', 'Richard Anderson')], limit=1)
        self.assertTrue(employee, "Employee is not created after clicking the 'Create Employee' button")
        self.assertEquals(employee.name, applicant.employee_name, "Employee name should be populated from applicant")
        # Custom fields with same names should be populated:
        self.assertEquals(employee.x_hobby, applicant.x_hobby)
        self.assertEquals(employee.x_bff, applicant.x_bff)
        self.assertEquals(employee.x_something_we_dont_ask_applicants, False,
                          "x_something_we_dont_ask_applicants should be blank - " +
                          "we certainly didn't ask it during recruitment")

    def create_field(self, model_name, name, *, field_type='char'):
        """ create a custom field and return it """
        model = self.env['ir.model'].search([('model', '=', model_name)])
        field = self.env['ir.model.fields'].create({
            'model_id': model.id,
            'name': name,
            'field_description': name,
            'ttype': field_type,
        })
        self.assertIn(name, self.env[model_name]._fields)
        return field
