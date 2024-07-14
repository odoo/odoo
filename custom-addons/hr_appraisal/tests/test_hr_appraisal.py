# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from odoo.tests.common import TransactionCase


class TestHrAppraisal(TransactionCase):
    """ Test used to check that when doing appraisal creation."""

    @classmethod
    def setUpClass(cls):
        super(TestHrAppraisal, cls).setUpClass()
        cls.HrEmployee = cls.env['hr.employee']
        cls.HrAppraisal = cls.env['hr.appraisal']
        cls.main_company = cls.env.ref('base.main_company')

        cls.dep_rd = cls.env['hr.department'].create({'name': 'RD Test'})
        cls.manager_user = cls.env['res.users'].create({
            'name': 'Manager User',
            'login': 'manager_user',
            'password': 'manager_user',
            'email': 'demo@demo.com',
            'partner_id': cls.env['res.partner'].create({'name': 'Manager Partner'}).id,
        })
        cls.manager = cls.env['hr.employee'].create({
            'name': 'Manager Test',
            'department_id': cls.dep_rd.id,
            'user_id': cls.manager_user.id,
        })

        cls.job = cls.env['hr.job'].create({'name': 'Developer Test', 'department_id': cls.dep_rd.id})
        cls.colleague = cls.env['hr.employee'].create({'name': 'Colleague Test', 'department_id': cls.dep_rd.id})

        group = cls.env.ref('hr_appraisal.group_hr_appraisal_user').id
        cls.user = cls.env['res.users'].create({
            'name': 'Michael Hawkins',
            'login': 'test',
            'groups_id': [(6, 0, [group])],
            'notification_type': 'email',
        })

        with freeze_time(date.today() + relativedelta(months=-6)):
            cls.hr_employee = cls.HrEmployee.create(dict(
                name="Michael Hawkins",
                user_id=cls.user.id,
                department_id=cls.dep_rd.id,
                parent_id=cls.manager.id,
                job_id=cls.job.id,
                work_phone="+3281813700",
                work_email='michael@odoo.com',
            ))
            cls.hr_employee.write({'work_location_id': [(0, 0, {'name': "Grand-Rosière"})]})

        cls.env.company.appraisal_plan = True
        cls.env['ir.config_parameter'].sudo().set_param("hr_appraisal.appraisal_create_in_advance_days", 8)
        cls.duration_after_recruitment = 6
        cls.duration_first_appraisal = 9
        cls.duration_next_appraisal = 12
        cls.env.company.write({
            'duration_after_recruitment': cls.duration_after_recruitment,
            'duration_first_appraisal': cls.duration_first_appraisal,
            'duration_next_appraisal': cls.duration_next_appraisal,
        })

    def test_hr_appraisal(self):
        with freeze_time(date.today() + relativedelta(months=6)):
            # I run the scheduler
            self.env['res.company']._run_employee_appraisal_plans()  # cronjob

            # I check whether new appraisal is created for above employee or not
            appraisals = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id)])
            self.assertTrue(appraisals, "Appraisal not created")

            # I start the appraisal process by click on "Start Appraisal" button.
            appraisals.action_confirm()

            # I check that state is "Appraisal Sent".
            self.assertEqual(appraisals.state, 'pending', "appraisal should be 'Appraisal Sent' state")
            # I check that "Final Interview Date" is set or not.
            self.env['calendar.event'].create({
                "name": "Appraisal Meeting",
                "start": datetime.now() + relativedelta(months=1),
                "stop": datetime.now() + relativedelta(months=1, hours=2),
                "duration": 2,
                "allday": False,
                'res_id': appraisals.id,
                'res_model_id': self.env.ref('hr_appraisal.model_hr_appraisal').id
            })
            self.assertTrue(appraisals.date_final_interview, "Interview Date is not created")
            # I check whether final interview meeting is created or not
            self.assertTrue(appraisals.meeting_ids, "Meeting is not linked")
            # I close this Apprisal
            appraisals.action_done()
            # I check that state of Appraisal is done.
            self.assertEqual(appraisals.state, 'done', "Appraisal should be in done state")

    def test_01_appraisal_next_appraisal_date(self):
        """
            An employee has just started working.
            Check that next_appraisal_date is set properly.
            Also, When there is ongoing appraisal for an employee,
            it means that there is no appraisal plan yet.
            Thus, next_appraisal_date should be empty.
        """
        self.hr_employee.create_date = date.today()
        self.hr_employee.last_appraisal_date = date.today()

        months = self.hr_employee.company_id.duration_after_recruitment
        upcoming_appraisal_date = date.today() + relativedelta(months=months)

        self.assertEqual(self.hr_employee.next_appraisal_date, upcoming_appraisal_date, 'next_appraisal_date is not set properly for an employee that has just started')

        # create appraisal manually
        self.HrAppraisal.create({
            'employee_id': self.hr_employee.id,
            'date_close': date.today() + relativedelta(months=1),
            'state': 'new'
        })
        self.assertEqual(self.hr_employee.next_appraisal_date, False, 'There is an ongoing appraisal for an employee, next_appraisal_date should be empty.')

    def test_appraisal_next_appraisal_date_uppcoming_appraisal(self):
        """
        Check that next_appraisal_date is correct and that indeed,
        appraisal plan generates appraisal at that time.
        """

        self.hr_employee.create_date = date.today()
        self.hr_employee.last_appraisal_date = date.today()

        month = self.hr_employee.company_id.duration_after_recruitment

        upcoming_appraisal_date = date.today() + relativedelta(months=month)

        self.assertEqual(self.hr_employee.next_appraisal_date, upcoming_appraisal_date, 'next_appraisal_date is not set properly')

        with freeze_time(self.hr_employee.next_appraisal_date):
            self.env['res.company']._run_employee_appraisal_plans()
            appraisals = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id)])
            self.assertTrue(appraisals, "Appraisal not created by appraisal plan at next_appraisal_date")

    def test_08_check_new_employee_no_appraisal(self):
        """
            Employee has started working recenlty
            less than duration_after_recruitment ago,
            check that appraisal is not set
        """
        self.hr_employee.create_date = date.today() - relativedelta(months=3)
        self.hr_employee.last_appraisal_date = date.today() - relativedelta(months=3)

        self.env['res.company']._run_employee_appraisal_plans()
        appraisals = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id)])
        self.assertFalse(appraisals, "Appraisal created")

    def test_09_check_appraisal_after_recruitment(self):
        """
            Employee has started working recently
            Time for a first appraisal after
            some time (duration_after_recruitment) has evolved
            since recruitment
        """
        with freeze_time(self.hr_employee.create_date + relativedelta(months=self.duration_after_recruitment)):
            self.env['res.company']._run_employee_appraisal_plans()
            appraisals = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id)])
            self.assertTrue(appraisals, "Appraisal not created")

    def test_10_check_no_appraisal_since_recruitment_appraisal(self):
        """
            After employees first recruitment appraisal some time has evolved,
            but not enough for the first real appraisal.
            Check that appraisal is not created
        """
        self.hr_employee.create_date = date.today() - relativedelta(months=self.duration_after_recruitment + 2, days=10)
        self.hr_employee.last_appraisal_date = date.today() - relativedelta(months=2, days=10)

        self.env['res.company']._run_employee_appraisal_plans()
        appraisals = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id)])
        self.assertFalse(appraisals, "Appraisal created")

    def test_11_check_first_appraisal_since_recruitment_appraisal(self):
        """
            Employee started while ago, has already had
            first recruitment appraisal and now it is
            time for a first real appraisal
        """
        self.hr_employee.create_date = date.today() - relativedelta(months=self.duration_after_recruitment + self.duration_first_appraisal, days=10)
        self.hr_employee.last_appraisal_date = date.today() - relativedelta(months=self.duration_first_appraisal, days=10)
        # In order to make the second appraisal, cron checks that
        # there is alraedy one done appraisal for the employee
        self.HrAppraisal.create({
            'employee_id': self.hr_employee.id,
            'date_close': date.today() - relativedelta(months=self.duration_first_appraisal, days=10),
            'state': 'done'
        })

        self.env['res.company']._run_employee_appraisal_plans()
        appraisals = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id)])
        self.assertTrue(appraisals, "Appraisal not created")

    def test_12_check_no_appraisal_after_first_appraisal(self):
        """
            Employee has already had first recruitment appraisal
            and first real appraisal, but its not time yet
            for recurring appraisal. Check that
            appraisal is not set
        """
        self.hr_employee.create_date = date.today() - relativedelta(months=self.duration_after_recruitment + self.duration_first_appraisal + 2, days=10)
        self.hr_employee.last_appraisal_date = date.today() - relativedelta(months=2, days=10)
        # In order to make recurring appraisal, cron checks that
        # there are alraedy two done appraisals for the employee
        self.HrAppraisal.create({
            'employee_id': self.hr_employee.id,
            'date_close': date.today() - relativedelta(months=self.duration_first_appraisal + 2, days=10),
            'state': 'done'
        })
        self.HrAppraisal.create({
            'employee_id': self.hr_employee.id,
            'date_close': date.today() - relativedelta(months=2, days=10),
            'state': 'done'
        })

        self.env['res.company']._run_employee_appraisal_plans()
        appraisals = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id), ('state', '=', 'new')])
        self.assertFalse(appraisals, "Appraisal created")

    def test_12_check_recurring_appraisal(self):
        """
            check that recurring appraisal is created
        """

        self.hr_employee.create_date = date.today() - relativedelta(months=self.duration_after_recruitment + self.duration_first_appraisal + self.duration_next_appraisal, days=10)
        self.hr_employee.last_appraisal_date = date.today() - relativedelta(months=self.duration_next_appraisal, days=10)

        self.HrAppraisal.create({
            'employee_id': self.hr_employee.id,
            'date_close': date.today() - relativedelta(months=self.duration_first_appraisal + self.duration_next_appraisal, days=10),
            'state': 'done'
        })
        self.HrAppraisal.create({
            'employee_id': self.hr_employee.id,
            'date_close': date.today() - relativedelta(months=self.duration_next_appraisal, days=10),
            'state': 'done'
        })

        self.env['res.company']._run_employee_appraisal_plans()
        appraisals = self.HrAppraisal.search([('employee_id', '=', self.hr_employee.id)])
        self.assertTrue(appraisals, "Appraisal not created")
