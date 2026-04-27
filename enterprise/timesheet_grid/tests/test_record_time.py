# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from datetime import date, timedelta

from odoo.tests import HttpCase, tagged

from odoo.addons.hr_timesheet.tests.test_timesheet import TestCommonTimesheet


@tagged('-at_install', 'post_install')
class TestRecordTime(TestCommonTimesheet, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env['project.project'].create({
            'name': 'Test Project'
        })

    def test_record_time(self):
        self.start_tour('/odoo', 'timesheet_record_time', login='admin', timeout=100)

    def test_timesheet_overtime(self):
        self.empl_employee.resource_calendar_id.flexible_hours = True
        # Get this week's Monday (or next Monday if today is Sunday)
        relevant_monday = date.today() + timedelta(
            days=-date.today().weekday() + (7 if date.today().weekday() == 6 else 0)
        )
        timesheets = self.env['account.analytic.line'].create([
            {
                'name': f"Test Timesheet {i+1}",
                'project_id': self.project_customer.id,
                'task_id': self.task1.id,
                'date': relevant_monday - timedelta(days=i),
                'unit_amount': 3.0 + i,
                'employee_id': self.empl_employee.id,
            }
            for i in range(8)
        ])

        self.start_tour('/odoo', 'timesheet_overtime_hour_encoding', login=self.user_employee.login, timeout=100)

        timesheets[6].write({'unit_amount': 0.0})

        self.env['res.config.settings'].create({'timesheet_encode_method': 'days'}).execute()
        self.start_tour('/odoo', 'timesheet_overtime_day_encoding', login=self.user_employee.login, timeout=100)

    def test_timesheet_availabilty_days(self):
        # Create company
        company = self.env['res.company'].create({'name': 'New Test Company'})

        # Create user
        test_user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
            'email': 'test@example.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
            'company_ids': [(6, 0, [company.id])],
            'company_id': company.id,
        })

        # Create flexible calendar
        calendar = self.env['resource.calendar'].create({
            'name': 'Calendar 8h',
            'tz': 'UTC',
            'full_time_required_hours': 8.0,
            'hours_per_day': 8.0,
            'flexible_hours': True,
        })

        # Create employee linked to user
        employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'user_id': test_user.id,
            'company_id': company.id,
            'resource_calendar_id': calendar.id,
        })

        # Ensure company calendar is NOT flexible (to avoid global override)
        company.resource_calendar_id = self.env['resource.calendar'].create({
            'name': 'Company Calendar (Rigid)',
            'flexible_hours': False,
        })

        # Call grid_unavailability() with the employee
        unavailable_days = self.env['account.analytic.line'].with_user(test_user).with_company(company).grid_unavailability(
            date.today(),
            date.today() + timedelta(days=7)
        )

        # No unavailable days for flexible schedule in my Timesheet
        self.assertFalse(len(unavailable_days[False]))

        # Call again, this time with groupby='employee_id'
        unavailable_days = self.env['account.analytic.line'].with_company(company).grid_unavailability(
            date.today(),
            date.today() + timedelta(days=7),
            groupby='employee_id',
            res_ids=[employee.id]
        )

        # Company availability
        self.assertTrue(len(unavailable_days[False]))
        self.assertFalse(unavailable_days[employee.id])
