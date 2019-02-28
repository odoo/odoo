# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.fields import Date
from odoo.tests.common import TransactionCase


class TestPayslipBase(TransactionCase):

    def setUp(self):
        super(TestPayslipBase, self).setUp()

        # Some salary rules references
        self.hra_rule_id = self.ref('hr_payroll.hr_salary_rule_houserentallowance1')
        self.conv_rule_id = self.ref('hr_payroll.hr_salary_rule_convanceallowance1')
        self.prof_tax_rule_id = self.ref('hr_payroll.hr_salary_rule_professionaltax1')
        self.pf_rule_id = self.ref('hr_payroll.hr_salary_rule_providentfund1')
        self.mv_rule_id = self.ref('hr_payroll.hr_salary_rule_meal_voucher')

        # I create a new employee "Richard"
        self.richard_emp = self.env['hr.employee'].create({
            'name': 'Richard',
            'gender': 'male',
            'birthday': '1984-05-01',
            'country_id': self.ref('base.be'),
            'department_id': self.ref('hr.dep_rd')
        })

        # I create a salary structure for "Software Developer"
        self.developer_pay_structure = self.env['hr.payroll.structure'].create({
            'name': 'Salary Structure for Software Developer',
            'code': 'SD',
            'rule_ids': [(4, self.hra_rule_id), (4, self.conv_rule_id),
                         (4, self.prof_tax_rule_id), (4, self.pf_rule_id),
                         (4, self.mv_rule_id)],
        })

        # I create a contract for "Richard"
        self.env['hr.contract'].create({
            'date_end': Date.to_string((datetime.now() + timedelta(days=365))),
            'date_start': Date.today(),
            'name': 'Contract for Richard',
            'wage': 5000.0,
            'employee_id': self.richard_emp.id,
            'struct_id': self.developer_pay_structure.id,
        })

        self.work_entry_type_leave = self.env['hr.work.entry.type'].create({
            'name': 'Leave',
            'is_leave': True,
            'code': 'LEAVE100'
        })
        self.leave_type = self.env['hr.leave.type'].create({
            'name': 'Legal Leaves',
            'time_type': 'leave',
            'allocation_type': 'no',
            'work_entry_type_id': self.work_entry_type_leave.id
        })

class TestPayslipContractBase(TestPayslipBase):

    def setUp(self):
        super(TestPayslipContractBase, self).setUp()
        self.calendar_richard = self.env['resource.calendar'].create({'name': 'Calendar of Richard'})
        self.calendar_40h = self.env['resource.calendar'].create({'name': 'Default calendar'})
        self.calendar_35h = self.env['resource.calendar'].create({
            'name': '35h calendar',
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Evening', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Evening', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Evening', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Evening', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Evening', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'})
            ]
        })
        self.calendar_35h._onchange_hours_per_day() # update hours/day
        self.richard_emp.resource_calendar_id = self.calendar_richard

        # This contract ends at the 15th of the month
        self.contract_cdd = self.env['hr.contract'].create({ # Fixed term contract
            'date_end': datetime.strptime('2015-11-15', '%Y-%m-%d'),
            'date_start': datetime.strptime('2015-01-01', '%Y-%m-%d'),
            'name': 'First CDD Contract for Richard',
            'resource_calendar_id': self.calendar_40h.id,
            'wage': 5000.0,
            'employee_id': self.richard_emp.id,
            'struct_id': self.developer_pay_structure.id,
            'state': 'close',
        })

        # This contract starts the next day
        self.contract_cdi = self.env['hr.contract'].create({ # Fixed term contract
            'date_start': datetime.strptime('2015-11-16', '%Y-%m-%d'),
            'name': 'Contract for Richard',
            'resource_calendar_id': self.calendar_35h.id,
            'wage': 5000.0,
            'employee_id': self.richard_emp.id,
            'struct_id': self.developer_pay_structure.id,
            'state': 'open',
        })
