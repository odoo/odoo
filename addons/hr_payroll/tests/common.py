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
        self.comm_rule_id = self.ref('hr_payroll.hr_salary_rule_sales_commission')

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
            'company_id': self.ref('base.main_company'),
            'rule_ids': [(4, [self.hra_rule_id, self.conv_rule_id, self.prof_tax_rule_id, self.pf_rule_id, self.mv_rule_id, self.comm_rule_id])]
        })

        # I create a contract for "Richard"
        self.env['hr.contract'].create({
            'date_end': Date.to_string((datetime.now() + timedelta(days=365))),
            'date_start': Date.today(),
            'name': 'Contract for Richard',
            'wage': 5000.0,
            'type_id': self.ref('hr_contract.hr_contract_type_emp'),
            'employee_id': self.richard_emp.id,
            'struct_id': self.developer_pay_structure.id,
            'working_hours': self.ref('resource.timesheet_group1')
        })


        # Prepare context with proper timezone information
        context = {
            "lang": "en_US", "tz": "UTC"
        }

        # Create another employee for test of the holiday calculations
        self.amanda_emp = self.env['hr.employee'].with_context(context).create({
            'name': 'Amanda',
            'gender': 'female',
            'birthday': '1982-08-15',
            'country_id': self.ref('base.be'),
            'department_id': self.ref('hr.dep_rd')
        })

        # Create work shcedule for 46 hours week
        self.calendar_46 = self.env['resource.calendar'].with_context(context).create({
            'name': '46 hours working week'
        })

        for i in range(0,5):
            self.env['resource.calendar.attendance'].with_context(context).create({
                'name': "Day {0} morning".format(i),
                'dayofweek': "{0}".format(i),
                'hour_from': 8,
                'hour_to': 12,
                'calendar_id': self.calendar_46.id
            })
            self.env['resource.calendar.attendance'].with_context(context).create({
                'name': "Day {0} afternoon".format(i),
                'dayofweek': "{0}".format(i),
                'hour_from': 13,
                'hour_to': 17,
                'calendar_id': self.calendar_46.id
            })
        self.env['resource.calendar.attendance'].with_context(context).create({
            'name': "Day 6",
            'dayofweek': "6",
            'hour_from': 12,
            'hour_to': 18,
            'calendar_id': self.calendar_46.id
        })

        # I create a contract for "Amanda"
        self.env['hr.contract'].with_context(context).create({
            'date_end': '2099-01-01',
            'date_start': '2010-01-01',
            'name': 'Contract for Amanda',
            'wage': 10000.0,
            'type_id': self.ref('hr_contract.hr_contract_type_emp'),
            'employee_id': self.amanda_emp.id,
            'struct_id': self.developer_pay_structure.id,
            'working_hours': self.calendar_46.id
        })

        self.holiday_s1 = self.env['hr.holidays.status'].with_context(context).create({
            'name': 'HOLIDAY_S1',
            'limit': True,
        })

        self.holiday_s2 = self.env['hr.holidays.status'].with_context(context).create({
            'name': 'HOLIDAY_S2',
            'limit': True,
        })

        self.holiday_s3 = self.env['hr.holidays.status'].with_context(context).create({
            'name': 'HOLIDAY_S3',
            'limit': True,
        })

        holiday = self.env['hr.holidays'].with_context(context).create({
            'name': 'Hol 4 hours in the morning',
            'employee_id': self.amanda_emp.id,
            'holiday_status_id': self.holiday_s1.id,
            'date_from': '2017-02-03 08:00:00',
            'date_to': '2017-02-03 12:00:00',
            'number_of_days_temp': 1,
        })
        holiday.action_approve()

        holiday = self.env['hr.holidays'].with_context(context).create({
            'name': 'Hol 4 hours in the 6 hour working day',
            'employee_id': self.amanda_emp.id,
            'holiday_status_id': self.holiday_s2.id,
            'date_from': '2017-02-05 12:00:00',
            'date_to': '2017-02-05 16:00:00',
            'number_of_days_temp': 1,
        })
        holiday.action_approve()

        holiday = self.env['hr.holidays'].with_context(context).create({
            'name': 'Hol 3 whole 3 days',
            'employee_id': self.amanda_emp.id,
            'holiday_status_id': self.holiday_s3.id,
            'date_from': '2017-02-12 00:00:00',
            'date_to': '2017-02-14 23:59:59',
            'number_of_days_temp': 3,
        })
        holiday.action_approve()
