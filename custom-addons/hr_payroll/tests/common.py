# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.fields import Date, Datetime
from odoo.tests.common import TransactionCase
from dateutil.relativedelta import relativedelta


class TestPayslipBase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestPayslipBase, cls).setUpClass()
        cls.env.company.country_id = cls.env.ref('base.us')
        cls.env.user.tz = 'Europe/Brussels'
        cls.env.ref('resource.resource_calendar_std').tz = 'Europe/Brussels'

        cls.dep_rd = cls.env['hr.department'].create({
            'name': 'Research & Development - Test',
        })

        # I create a new employee "Richard"
        cls.richard_emp = cls.env['hr.employee'].create({
            'name': 'Richard',
            'gender': 'male',
            'birthday': '1984-05-01',
            'country_id': cls.env.ref('base.be').id,
            'department_id': cls.dep_rd.id,
        })

        # I create a new employee "Jules"
        cls.jules_emp = cls.env['hr.employee'].create({
            'name': 'Jules',
            'gender': 'male',
            'birthday': '1984-05-01',
            'country_id': cls.env.ref('base.be').id,
            'department_id': cls.dep_rd.id,
        })

        cls.structure_type = cls.env['hr.payroll.structure.type'].create({
            'name': 'Test - Developer',
        })

        # I create a contract for "Richard"
        cls.env['hr.contract'].create({
            'date_end': Date.today() + relativedelta(years=2),
            'date_start': Date.to_date('2018-01-01'),
            'name': 'Contract for Richard',
            'wage': 5000.33,
            'employee_id': cls.richard_emp.id,
            'structure_type_id': cls.structure_type.id,
        })

        cls.work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Extra attendance',
            'is_leave': False,
            'code': 'WORKTEST200',
        })

        cls.work_entry_type_unpaid = cls.env['hr.work.entry.type'].create({
            'name': 'Unpaid Leave',
            'is_leave': True,
            'code': 'LEAVETEST300',
            'round_days': 'HALF',
            'round_days_type': 'DOWN',
        })

        cls.work_entry_type_leave = cls.env['hr.work.entry.type'].create({
            'name': 'Leave',
            'is_leave': True,
            'code': 'LEAVETEST100'
        })

        # I create a salary structure for "Software Developer"
        cls.developer_pay_structure = cls.env['hr.payroll.structure'].create({
            'name': 'Salary Structure for Software Developer',
            'type_id': cls.structure_type.id,
            'unpaid_work_entry_type_ids': [(4, cls.work_entry_type_unpaid.id, False)]
        })

        cls.hra_rule = cls.env['hr.salary.rule'].create({
            'name': 'House Rent Allowance',
            'sequence': 5,
            'amount_select': 'percentage',
            'amount_percentage': 40.0,
            'amount_percentage_base': 'contract.wage',
            'code': 'HRA',
            'category_id': cls.env.ref('hr_payroll.ALW').id,
            'struct_id': cls.developer_pay_structure.id,
        })

        cls.conv_rule = cls.env['hr.salary.rule'].create({
            'name': 'Conveyance Allowance',
            'sequence': 10,
            'amount_select': 'fix',
            'amount_fix': 800.0,
            'code': 'CA',
            'category_id': cls.env.ref('hr_payroll.ALW').id,
            'struct_id': cls.developer_pay_structure.id,
        })

        cls.mv_rule = cls.env['hr.salary.rule'].create({
            'name': 'Meal Voucher',
            'sequence': 16,
            'amount_select': 'fix',
            'amount_fix': 10,
            'quantity': "'WORK100' in worked_days and worked_days['WORK100'].number_of_days",
            'code': 'MA',
            'category_id': cls.env.ref('hr_payroll.ALW').id,
            'struct_id': cls.developer_pay_structure.id,
        })

        cls.sum_of_alw = cls.env['hr.salary.rule'].create({
            'name': 'Sum of Allowance category',
            'sequence': 99,
            'amount_select': 'code',
            'amount_python_compute': "result = payslip._sum_category('ALW', payslip.date_from, to_date=payslip.date_to)",
            'quantity': "'WORK100' in worked_days and worked_days['WORK100'].number_of_days",
            'code': 'SUMALW',
            'category_id': cls.env.ref('hr_payroll.ALW').id,
            'struct_id': cls.developer_pay_structure.id,
        })

        cls.pf_rule = cls.env['hr.salary.rule'].create({
            'name': 'Provident Fund',
            'sequence': 120,
            'amount_select': 'percentage',
            'amount_percentage': -12.5,
            'amount_percentage_base': 'contract.wage',
            'code': 'PF',
            'category_id': cls.env.ref('hr_payroll.DED').id,
            'struct_id': cls.developer_pay_structure.id,
        })

        cls.prof_tax_rule = cls.env['hr.salary.rule'].create({
            'name': 'Professional Tax',
            'sequence': 150,
            'amount_select': 'fix',
            'amount_fix': -200.0,
            'code': 'PT',
            'category_id': cls.env.ref('hr_payroll.DED').id,
            'struct_id': cls.developer_pay_structure.id,
        })
        cls.structure_type.default_struct_id = cls.developer_pay_structure

    def create_work_entry(self, start, stop, work_entry_type=None):
        work_entry_type = work_entry_type or self.work_entry_type
        return self.env['hr.work.entry'].create({
            'contract_id': self.richard_emp.contract_ids[0].id,
            'name': "Work entry %s-%s" % (start, stop),
            'date_start': start,
            'date_stop': stop,
            'employee_id': self.richard_emp.id,
            'work_entry_type_id': work_entry_type.id,
        })


class TestPayslipContractBase(TestPayslipBase):

    @classmethod
    def setUpClass(cls):
        super(TestPayslipContractBase, cls).setUpClass()
        cls.calendar_richard = cls.env['resource.calendar'].create({'name': 'Calendar of Richard'})
        cls.calendar_40h = cls.env['resource.calendar'].create({'name': 'Default calendar'})
        cls.calendar_38h = cls.env['resource.calendar'].create({
            'name': 'Standard 38 hours/week',
            'tz': 'Europe/Brussels',
            'company_id': False,
            'hours_per_day': 7.6,
            'attendance_ids': [(5, 0, 0),
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'})
            ],
        })
        cls.calendar_35h = cls.env['resource.calendar'].create({
            'name': '35h calendar',
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Evening', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Evening', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Wednesday Evening', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Evening', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Friday Evening', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'})
            ]
        })

        cls.calendar_2_weeks = cls.env['resource.calendar'].create({
            'name': 'Week 1: 30 Hours - Week 2: 16 Hours',
            'two_weeks_calendar': True,
            'attendance_ids': [
                (0, 0, {'name': 'Monday', 'sequence': '1', 'week_type': '0', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 16}),
                (0, 0, {'name': 'Monday', 'sequence': '26', 'week_type': '1', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 16}),
                (0, 0, {'name': 'Tuesday', 'sequence': '2', 'week_type': '0', 'dayofweek': '1', 'hour_from': 9, 'hour_to': 17}),
                (0, 0, {'name': 'Wednesday', 'sequence': '27', 'week_type': '1', 'dayofweek': '2', 'hour_from': 7, 'hour_to': 15}),
                (0, 0, {'name': 'Thursday', 'sequence': '28', 'week_type': '1', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 16}),
                (0, 0, {'name': 'Friday', 'sequence': '29', 'week_type': '1', 'dayofweek': '4', 'hour_from': 10, 'hour_to': 18}),
                (0, 0, {'name': 'Even week', 'dayofweek': '0', 'sequence': '0', 'hour_from': 0, 'day_period': 'morning', 'week_type': '0', 'hour_to': 0, 'display_type': 'line_section'}),
                (0, 0, {'name': 'Odd week', 'dayofweek': '0', 'sequence': '25', 'hour_from': 0, 'day_period': 'morning', 'week_type': '1', 'hour_to': 0, 'display_type': 'line_section'}),
            ]
        })

        cls.richard_emp.resource_calendar_id = cls.calendar_richard
        cls.jules_emp.resource_calendar_id = cls.calendar_2_weeks

        cls.calendar_16h = cls.env['resource.calendar'].create({
            'name': '16h calendar',
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 11.5, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 11.5, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 11.5, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 9, 'hour_to': 12.5, 'day_period': 'morning', 'duration_days': 3.5/5.5}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12.5, 'hour_to': 13.5, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Evening', 'dayofweek': '3', 'hour_from': 13.5, 'hour_to': 15.5, 'day_period': 'afternoon', 'duration_days': 2/5.5}),
            ]
        })

        cls.calendar_38h_friday_light = cls.env['resource.calendar'].create({
            'name': '38 calendar Friday light',
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'duration_days': 4/8.5}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Evening', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17.5, 'day_period': 'afternoon', 'duration_days': 4.5/8.5}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'duration_days': 4/8.5}),
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Evening', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17.5, 'day_period': 'afternoon', 'duration_days': 4.5/8.5}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'duration_days': 4/8.5}),
                (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Wednesday Evening', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17.5, 'day_period': 'afternoon', 'duration_days': 4.5/8.5}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'duration_days': 4/8.5}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Evening', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17.5, 'day_period': 'afternoon', 'duration_days': 4.5/8.5}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning', 'duration_days': 1}),
            ]
        })

        # This contract ends at the 15th of the month
        cls.contract_cdd = cls.env['hr.contract'].create({ # Fixed term contract
            'date_end': datetime.strptime('2015-11-15', '%Y-%m-%d'),
            'date_start': datetime.strptime('2015-01-01', '%Y-%m-%d'),
            'name': 'First CDD Contract for Richard',
            'resource_calendar_id': cls.calendar_40h.id,
            'wage': 5000.33,
            'employee_id': cls.richard_emp.id,
            'structure_type_id': cls.structure_type.id,
            'state': 'open',
            'kanban_state': 'blocked',
            'date_generated_from': datetime.strptime('2015-11-16', '%Y-%m-%d'),
            'date_generated_to': datetime.strptime('2015-11-16', '%Y-%m-%d'),
        })

        # This contract starts the next day
        cls.contract_cdi = cls.env['hr.contract'].create({
            'date_start': datetime.strptime('2015-11-16', '%Y-%m-%d'),
            'name': 'Contract for Richard',
            'resource_calendar_id': cls.calendar_35h.id,
            'wage': 5000.33,
            'employee_id': cls.richard_emp.id,
            'structure_type_id': cls.structure_type.id,
            'state': 'open',
            'kanban_state': 'normal',
            'date_generated_from': datetime.strptime('2015-11-15', '%Y-%m-%d'),
            'date_generated_to': datetime.strptime('2015-11-15', '%Y-%m-%d'),
        })

        # Contract for Jules
        cls.contract_jules = cls.env['hr.contract'].create({
            'date_start': datetime.strptime('2015-01-01', '%Y-%m-%d'),
            'name': 'Contract for Jules',
            'resource_calendar_id': cls.calendar_2_weeks.id,
            'wage': 5000.33,
            'employee_id': cls.jules_emp.id,
            'structure_type_id': cls.developer_pay_structure.type_id.id,
            'state': 'open',
        })
