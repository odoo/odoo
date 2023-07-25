# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('company_leave')
class TestCompanyLeave(TransactionCase):
    """ Test leaves for a whole company, conflict resolutions """

    @classmethod
    def setUpClass(cls):
        super(TestCompanyLeave, cls).setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'A company'})

        cls.bank_holiday = cls.env['hr.leave.type'].create({
            'name': 'Bank Holiday',
            'responsible_id': cls.env.user.id,
            'company_id': cls.company.id,
            'requires_allocation': 'no',
        })

        cls.paid_time_off = cls.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'request_unit': 'day',
            'leave_validation_type': 'both',
            'company_id': cls.company.id,
            'requires_allocation': 'no',
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'My Employee',
            'company_id': cls.company.id,
        })

    def test_leave_whole_company_01(self):
        # TEST CASE 1: Leaves taken in days. Take a 3 days leave
        # Add a company leave on the second day.
        # Check that leave is split into 2.

        leave = self.env['hr.leave'].create({
            'name': 'Hol11',
            'employee_id': self.employee.id,
            'holiday_status_id': self.paid_time_off.id,
            'request_date_from': date(2020, 1, 7),
            'date_from': date(2020, 1, 7),
            'request_date_to': date(2020, 1, 9),
            'date_to': date(2020, 1, 9),
            'number_of_days': 3,
        })
        leave._compute_date_from_to()

        company_leave = self.env['hr.leave'].create({
            'name': 'Bank Holiday',
            'holiday_type': 'company',
            'mode_company_id': self.company.id,
            'holiday_status_id': self.bank_holiday.id,
            'date_from': date(2020, 1, 8),
            'request_date_from': date(2020, 1, 8),
            'date_to': date(2020, 1, 8),
            'request_date_to': date(2020, 1, 8),
            'number_of_days': 1,
        })
        company_leave._compute_date_from_to()

        company_leave.action_validate()

        all_leaves = self.env['hr.leave'].search([('employee_id', '=', self.employee.id)], order='id')
        self.assertEqual(len(all_leaves), 4)
        # Original Leave
        self.assertEqual(leave.state, 'refuse')
        # before leave
        self.assertEqual(all_leaves[1].date_from, datetime(2020, 1, 7, 7, 0))
        self.assertEqual(all_leaves[1].date_to, datetime(2020, 1, 7, 16, 0))
        self.assertEqual(all_leaves[1].number_of_days, 1)
        self.assertEqual(all_leaves[1].state, 'confirm')
        # After leave
        self.assertEqual(all_leaves[2].date_from, datetime(2020, 1, 9, 7, 0))
        self.assertEqual(all_leaves[2].date_to, datetime(2020, 1, 9, 16, 0))
        self.assertEqual(all_leaves[2].number_of_days, 1)
        self.assertEqual(all_leaves[2].state, 'confirm')
        # Company Leave
        self.assertEqual(all_leaves[3].date_from, datetime(2020, 1, 8, 7, 0))
        self.assertEqual(all_leaves[3].date_to, datetime(2020, 1, 8, 16, 0))
        self.assertEqual(all_leaves[3].number_of_days, 1)
        self.assertEqual(all_leaves[3].state, 'validate')


    def test_leave_whole_company_02(self):
        # TEST CASE 2: Leaves taken in half-days. Take a 3 days leave
        # Add a company leave on the second day
        # Check that leave is split into 2
        self.paid_time_off.request_unit = 'half_day'

        leave = self.env['hr.leave'].create({
            'name': 'Hol11',
            'employee_id': self.employee.id,
            'holiday_status_id': self.paid_time_off.id,
            'request_date_from': date(2020, 1, 7),
            'date_from': date(2020, 1, 7),
            'request_date_to': date(2020, 1, 9),
            'date_to': date(2020, 1, 9),
            'number_of_days': 3,
        })
        leave._compute_date_from_to()

        company_leave = self.env['hr.leave'].create({
            'name': 'Bank Holiday',
            'holiday_type': 'company',
            'mode_company_id': self.company.id,
            'holiday_status_id': self.bank_holiday.id,
            'date_from': date(2020, 1, 8),
            'request_date_from': date(2020, 1, 8),
            'date_to': date(2020, 1, 8),
            'request_date_to': date(2020, 1, 8),
            'number_of_days': 1,
        })
        company_leave._compute_date_from_to()

        company_leave.action_validate()

        all_leaves = self.env['hr.leave'].search([('employee_id', '=', self.employee.id)], order='id')
        self.assertEqual(len(all_leaves), 4)
        # Original Leave
        self.assertEqual(leave.state, 'refuse')
        # before leave
        self.assertEqual(all_leaves[1].date_from, datetime(2020, 1, 7, 7, 0))
        self.assertEqual(all_leaves[1].date_to, datetime(2020, 1, 7, 16, 0))
        self.assertEqual(all_leaves[1].number_of_days, 1)
        self.assertEqual(all_leaves[1].state, 'confirm')
        # After leave
        self.assertEqual(all_leaves[2].date_from, datetime(2020, 1, 9, 7, 0))
        self.assertEqual(all_leaves[2].date_to, datetime(2020, 1, 9, 16, 0))
        self.assertEqual(all_leaves[2].number_of_days, 1)
        self.assertEqual(all_leaves[2].state, 'confirm')
        # Company Leave
        self.assertEqual(all_leaves[3].date_from, datetime(2020, 1, 8, 7, 0))
        self.assertEqual(all_leaves[3].date_to, datetime(2020, 1, 8, 16, 0))
        self.assertEqual(all_leaves[3].number_of_days, 1)
        self.assertEqual(all_leaves[3].state, 'validate')

    def test_leave_whole_company_03(self):
        # TEST CASE 3: Leaves taken in half-days. Take a 0.5 days leave
        # Add a company leave on the same day
        # Check that leave refused
        self.paid_time_off.request_unit = 'half_day'

        leave = self.env['hr.leave'].create({
            'name': 'Hol11',
            'employee_id': self.employee.id,
            'holiday_status_id': self.paid_time_off.id,
            'request_date_from': date(2020, 1, 7),
            'request_date_to': date(2020, 1, 7),
            'number_of_days': 0.5,
            'request_unit_half': True,
            'request_date_from_period': 'am',

        })
        leave._compute_date_from_to()

        company_leave = self.env['hr.leave'].create({
            'name': 'Bank Holiday',
            'holiday_type': 'company',
            'mode_company_id': self.company.id,
            'holiday_status_id': self.bank_holiday.id,
            'date_from': date(2020, 1, 7),
            'request_date_from': date(2020, 1, 7),
            'date_to': date(2020, 1, 7),
            'request_date_to': date(2020, 1, 7),
            'number_of_days': 1,
        })
        company_leave._compute_date_from_to()

        company_leave.action_validate()

        all_leaves = self.env['hr.leave'].search([('employee_id', '=', self.employee.id)], order='id')
        self.assertEqual(len(all_leaves), 2)
        # Original Leave
        self.assertEqual(leave.state, 'refuse')
        # Company Leave
        self.assertEqual(all_leaves[1].date_from, datetime(2020, 1, 7, 7, 0))
        self.assertEqual(all_leaves[1].date_to, datetime(2020, 1, 7, 16, 0))
        self.assertEqual(all_leaves[1].number_of_days, 1)
        self.assertEqual(all_leaves[1].state, 'validate')

    def test_leave_whole_company_04(self):
        # TEST CASE 4: Leaves taken in days. Take a 1 days leave
        # Add a company leave on the same day
        # Check that leave is refused
        self.paid_time_off.request_unit = 'day'

        leave = self.env['hr.leave'].create({
            'name': 'Hol11',
            'employee_id': self.employee.id,
            'holiday_status_id': self.paid_time_off.id,
            'request_date_from': date(2020, 1, 9),
            'request_date_to': date(2020, 1, 9),
            'number_of_days': 1,

        })
        leave._compute_date_from_to()

        company_leave = self.env['hr.leave'].create({
            'name': 'Bank Holiday',
            'holiday_type': 'company',
            'mode_company_id': self.company.id,
            'holiday_status_id': self.bank_holiday.id,
            'date_from': date(2020, 1, 9),
            'request_date_from': date(2020, 1, 9),
            'date_to': date(2020, 1, 9),
            'request_date_to': date(2020, 1, 9),
            'number_of_days': 1,
        })
        company_leave._compute_date_from_to()

        company_leave.action_validate()

        all_leaves = self.env['hr.leave'].search([('employee_id', '=', self.employee.id)], order='id')
        self.assertEqual(len(all_leaves), 2)
        # Original Leave
        self.assertEqual(leave.state, 'refuse')
        # Company Leave
        self.assertEqual(all_leaves[1].date_from, datetime(2020, 1, 9, 7, 0))
        self.assertEqual(all_leaves[1].date_to, datetime(2020, 1, 9, 16, 0))
        self.assertEqual(all_leaves[1].number_of_days, 1)
        self.assertEqual(all_leaves[1].state, 'validate')

    def test_leave_whole_company_06(self):
        # Test case 6: Leaves taken in days. But the employee
        # only works on Monday, Wednesday and Friday
        # Takes a time off for all the week (3 days), should be split

        self.employee.resource_calendar_id.write({'attendance_ids': [
            (5, 0, 0),
            (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'})
        ]})

        leave = self.env['hr.leave'].create({
            'name': 'Hol11',
            'employee_id': self.employee.id,
            'holiday_status_id': self.paid_time_off.id,
            'request_date_from': date(2020, 1, 6),
            'request_date_to': date(2020, 1, 10),
            'number_of_days': 3,
        })
        leave._compute_date_from_to()

        company_leave = self.env['hr.leave'].create({
            'name': 'Bank Holiday',
            'holiday_type': 'company',
            'mode_company_id': self.company.id,
            'holiday_status_id': self.bank_holiday.id,
            'date_from': date(2020, 1, 10),
            'request_date_from': date(2020, 1, 10),
            'date_to': date(2020, 1, 10),
            'request_date_to': date(2020, 1, 10),
            'number_of_days': 1,
        })
        company_leave._compute_date_from_to()
        company_leave.action_validate()

        all_leaves = self.env['hr.leave'].search([('employee_id', '=', self.employee.id)], order='id')
        self.assertEqual(len(all_leaves), 3)
        # Original Leave
        self.assertEqual(leave.state, 'refuse')
        # before leave
        self.assertEqual(all_leaves[1].date_from, datetime(2020, 1, 6, 7, 0))
        self.assertEqual(all_leaves[1].date_to, datetime(2020, 1, 9, 16, 0))
        self.assertEqual(all_leaves[1].number_of_days, 2)
        self.assertEqual(all_leaves[1].state, 'confirm')
        # Company Leave
        self.assertEqual(all_leaves[2].date_from, datetime(2020, 1, 10, 7, 0))
        self.assertEqual(all_leaves[2].date_to, datetime(2020, 1, 10, 16, 0))
        self.assertEqual(all_leaves[2].number_of_days, 1)
        self.assertEqual(all_leaves[2].state, 'validate')

    def test_leave_whole_company_07(self):
        # Test Case 7: Try to create a bank holidays for a lot of
        # employees, and check the performances
        # 100 employees - 15 already on holidays that day

        employees = self.env['hr.employee'].create([{
            'name': 'Employee %s' % i,
            'company_id': self.company.id
        } for i in range(100)])

        leaves = self.env['hr.leave'].create([{
            'name': 'Holiday - %s' % employee.name,
            'employee_id': employee.id,
            'holiday_status_id': self.paid_time_off.id,
            'request_date_from': date(2020, 3, 29),
            'date_from': datetime(2020, 3, 29, 7, 0, 0),
            'request_date_to': date(2020, 4, 1),
            'date_to': datetime(2020, 4, 1, 19, 0, 0),
            'number_of_days': 3,
        } for employee in employees[0:15]])
        leaves._compute_date_from_to()

        company_leave = self.env['hr.leave'].create({
            'name': 'Bank Holiday',
            'holiday_type': 'company',
            'mode_company_id': self.company.id,
            'holiday_status_id': self.bank_holiday.id,
            'date_from': date(2020, 4, 1),
            'request_date_from': date(2020, 4, 1),
            'date_to': date(2020, 4, 1),
            'request_date_to': date(2020, 4, 1),
            'number_of_days': 1,
        })
        company_leave._compute_date_from_to()

        with self.assertQueryCount(__system__=774, admin=867):  # 770 community
            # Original query count: 1987
            # Without tracking/activity context keys: 5154
            company_leave.action_validate()

        leaves = self.env['hr.leave'].search([('holiday_status_id', '=', self.bank_holiday.id)])
        self.assertEqual(len(leaves), 102)
