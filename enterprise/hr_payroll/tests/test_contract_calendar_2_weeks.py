# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo.addons.hr_payroll.tests.common import TestPayslipContractBase
from odoo.tests import tagged

@tagged('2_weeks_calendar')
class TestPayslipContractCalendar2Weeks(TestPayslipContractBase):

    def test_contract_2_weeks(self):
        # Create a payslip for a month with a contract with 2 weeks period.
        payslip = self.env['hr.payslip'].create({
            'name': 'November 2015',
            'employee_id': self.jules_emp.id,
            'date_from': datetime.strptime('2015-11-01', '%Y-%m-%d'),
            'date_to': datetime.strptime('2015-11-30', '%Y-%m-%d'),
        })
        self.assertEqual(payslip.worked_days_line_ids.number_of_hours, 104, "It should be 104 hours of work this month for this contract")
        self.assertEqual(payslip.worked_days_line_ids.number_of_days, 13, "It should be 13 days of work this month for this contract")

    def test_contract_2_weeks_holiday(self):
        # Leave during small week (just 2 days of work)
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'leave name',
            'date_from': datetime.strptime('2015-11-8 07:00:00', '%Y-%m-%d %H:%M:%S'),
            'date_to': datetime.strptime('2015-11-14 18:00:00', '%Y-%m-%d %H:%M:%S'),
            'resource_id': self.jules_emp.resource_id.id,
            'calendar_id': self.calendar_2_weeks.id,
            'work_entry_type_id': self.work_entry_type_leave.id,
            'time_type': 'leave',
        })
        payslip = self.env['hr.payslip'].create({
            'name': 'November 2015',
            'employee_id': self.jules_emp.id,
            'date_from': datetime.strptime('2015-11-01', '%Y-%m-%d'),
            'date_to': datetime.strptime('2015-11-30', '%Y-%m-%d'),
        })
        work = payslip.worked_days_line_ids.filtered(lambda line: line.code == 'WORK100')
        leave = payslip.worked_days_line_ids.filtered(lambda line: line.code == 'LEAVETEST100')
        self.assertEqual(work.number_of_hours, 88, "It should be 88 hours of work this month for this contract")
        self.assertEqual(leave.number_of_hours, 16, "It should be 16 hours of leave this month for this contract")
        self.assertEqual(work.number_of_days, 11, "It should be 11 days of work this month for this contract")
        self.assertEqual(leave.number_of_days, 2, "It should be 2 days of leave this month for this contract")

    def test_contract_2_big_weeks_holiday(self):
        # Leave during big week (4 days of work)
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'leave name',
            'date_from': datetime.strptime('2015-11-15 07:00:00', '%Y-%m-%d %H:%M:%S'),
            'date_to': datetime.strptime('2015-11-21 18:00:00', '%Y-%m-%d %H:%M:%S'),
            'resource_id': self.jules_emp.resource_id.id,
            'calendar_id': self.calendar_2_weeks.id,
            'work_entry_type_id': self.work_entry_type_leave.id,
            'time_type': 'leave',
        })
        payslip = self.env['hr.payslip'].create({
            'name': 'November 2015',
            'employee_id': self.jules_emp.id,
            'date_from': datetime.strptime('2015-11-01', '%Y-%m-%d'),
            'date_to': datetime.strptime('2015-11-30', '%Y-%m-%d'),
        })
        work = payslip.worked_days_line_ids.filtered(lambda line: line.code == 'WORK100')
        leave = payslip.worked_days_line_ids.filtered(lambda line: line.code == 'LEAVETEST100')
        self.assertEqual(work.number_of_hours, 72, "It should be 72 hours of work this month for this contract")
        self.assertEqual(leave.number_of_hours, 32, "It should be 32 hours of leave this month for this contract")
        self.assertEqual(work.number_of_days, 9, "It should be 9 days of work this month for this contract")
        self.assertEqual(leave.number_of_days, 4, "It should be 4 days of leave this month for this contract")
