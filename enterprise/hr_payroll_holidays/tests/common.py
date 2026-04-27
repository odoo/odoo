# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Date
from odoo.tests.common import TransactionCase, new_test_user

from dateutil.relativedelta import relativedelta


class TestPayrollHolidaysBase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.company_id.resource_calendar_id.tz = "Europe/Brussels"
        cls.env.context = {'tz': 'Europe/Brussels'}
        cls.dep_rd = cls.env['hr.department'].create({
            'name': 'Research & Development - Test',
        })

        # Create employee
        cls.vlad = new_test_user(cls.env, login='vlad', groups='base.group_user')
        cls.emp = cls.env['hr.employee'].create({
            'name': 'Donald',
            'gender': 'male',
            'birthday': '1946-06-14',
            'department_id': cls.dep_rd.id,
            'user_id': cls.vlad.id,
        })

        cls.joseph = new_test_user(cls.env, login='joseph', groups='base.group_user,hr_holidays.group_hr_holidays_user')

        cls.structure_type = cls.env['hr.payroll.structure.type'].create({
            'name': 'Test - Developer',
        })

        # Create his contract
        cls.env['hr.contract'].create({
            'date_end': Date.today() + relativedelta(years=2),
            'date_start': Date.to_date('2018-01-01'),
            'name': 'Contract for Donald',
            'wage': 5000.0,
            'employee_id': cls.emp.id,
            'structure_type_id': cls.structure_type.id,
            'state': 'open',
        })

        cls.work_entry_type_unpaid = cls.env['hr.work.entry.type'].create({
            'name': 'Unpaid Leave',
            'is_leave': True,
            'code': 'LEAVETEST300',
            'round_days': 'HALF',
            'round_days_type': 'DOWN',
        })

        # Create a salary structure, necessary to compute sheet
        cls.developer_pay_structure = cls.env['hr.payroll.structure'].create({
            'name': 'Salary Structure for Software Developer',
            'type_id': cls.structure_type.id,
            'unpaid_work_entry_type_ids': [(4, cls.work_entry_type_unpaid.id, False)]
        })
        cls.structure_type.default_struct_id = cls.developer_pay_structure

        # Create a leave type for our leaves
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Unpaid leave',
            'work_entry_type_id': cls.work_entry_type_unpaid.id,
            'time_type': 'leave',
            'requires_allocation': 'no',
        })
