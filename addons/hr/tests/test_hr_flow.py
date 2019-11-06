# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr.tests.common import TestHrCommon


class TestHrFlow(TestHrCommon):

    def setUp(self):
        super(TestHrFlow, self).setUp()
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

    def test_open2recruit2close_job(self):

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
