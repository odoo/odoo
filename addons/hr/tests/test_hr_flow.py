# -*- coding: utf-8 -*-

from openerp.addons.hr.tests.common import TestHrCommon


class TestHrFlow(TestHrCommon):

    def test_00_create_employee(self):
        """ Creating an employee with "HR Officer" rights. """

        self.env['hr.employee'].sudo(user=self.res_users_hr_officer.id).create({
            'name': 'Nicolas',
            'address_id': self.main_partner_id,
            'company_id': self.main_company_id,
            'department_id': self.rd_department_id,
            'user_id': self.demo_user_id
        })

    def test_10_open2recruit2close_job(self):
        """ Checking the recruitment process(open, recruit, close) for the job position "Developer". """

        """ Opening the job position for "Developer" and checking the job status and recruitment count. """
        self.job_developer.set_open()
        self.assertEqual(self.job_developer.state, 'open', "Job position of 'Job Developer' is in 'open' state.")
        self.assertEqual(self.job_developer.no_of_recruitment, 0,
             "Wrong number of recruitment for the job 'Job Developer'(%s found instead of 0)."
             % self.job_developer.no_of_recruitment)

        """ Recruiting employee "NIV" for the job position "Developer" and checking the job status and recruitment count. """
        self.job_developer.set_recruit()
        self.assertEqual(self.job_developer.state, 'recruit', "Job position of 'Job Developer' is in 'recruit' state.")
        self.assertEqual(self.job_developer.no_of_recruitment, 1,
             "Wrong number of recruitment for the job 'Job Developer'(%s found instead of 1.0)."
             % self.job_developer.no_of_recruitment)

        self.employee_niv.write({'job_id': self.job_developer.id})

        """ Closing the recruitment for the job position "Developer" by marking it as open. """
        self.job_developer.set_open()
        self.assertEqual(self.job_developer.state, 'open', "Job position of 'Job Developer' is in 'open' state.")
        self.assertEqual(self.job_developer.no_of_recruitment, 0,
             "Wrong number of recruitment for the job 'Job Developer'(%s found instead of 0)."
             % self.job_developer.no_of_recruitment)
