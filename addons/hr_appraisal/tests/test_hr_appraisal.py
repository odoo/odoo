# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta

from openerp import fields
from openerp.tests.common import TransactionCase


class TestHrAppraisal(TransactionCase):
    """ Test used to check that when doing appraisal creation."""

    def setUp(self):
        super(TestHrAppraisal, self).setUp()
        self.HrEmployee = self.env['hr.employee']
        self.HrAppraisal = self.env['hr.appraisal']
        self.main_company = self.env.ref('base.main_company')

    def test_hr_appraisal(self):
        # I create a new Employee with appraisal configuration.
        self.hr_employee = self.HrEmployee.create(dict(
            name="Michael Hawkins",
            department_id=self.env.ref('hr.dep_rd').id,
            parent_id=self.env.ref('hr.employee_al').id,
            job_id=self.env.ref('hr.job_developer').id,
            work_location="Grand-Rosière",
            work_phone="+3281813700",
            work_email='michael@openerp.com',
            appraisal_by_manager=True,
            appraisal_manager_ids=[self.env.ref('hr.employee_al').id],
            appraisal_manager_survey_id=self.env.ref('survey.feedback_form').id,
            appraisal_by_colleagues=True,
            appraisal_colleagues_ids=[self.env.ref('hr.employee_stw')],
            appraisal_colleagues_survey_id=self.env.ref('hr_appraisal.opinion_form').id,
            appraisal_self=True,
            appraisal_self_survey_id=self.env.ref('hr_appraisal.appraisal_form').id,
            periodic_appraisal=True,
            appraisal_frequency=1,
            appraisal_frequency_unit='year',
            appraisal_date=date.today() + relativedelta(days=5)
        ))

        # I run the scheduler
        self.HrEmployee.run_employee_appraisal()  # cronjob

        # I check whether new appraisal is created for above employee or not
        appraisals = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id)])
        self.assertTrue(appraisals, "Appraisal not created")

        # I start the appraisal process by click on "Start Appraisal" button.
        appraisals.button_send_appraisal()

        # I check that state is "Appraisal Sent".
        self.assertEqual(appraisals.state, 'pending', "appraisal should be 'Appraisal Sent' state")
        # I check that "Final Interview Date" is set or not.
        appraisals.write({'date_final_interview': str(date.today() + relativedelta(months=1))})
        self.assertTrue(appraisals.date_final_interview, "Interview Date is not created")
        # I check whether final interview meeting is created or not
        appraisals = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id)])
        self.assertTrue(appraisals.meeting_id, "Meeting is not created")
        # I close this Apprisal
        appraisals.write({'state': 'done'})
        # I check that state of Appraisal is done.
        self.assertEqual(appraisals.state, 'done', "Appraisal should be in done state")
