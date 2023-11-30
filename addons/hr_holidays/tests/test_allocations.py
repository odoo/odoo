# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged('allocation')
class TestAllocations(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super(TestAllocations, cls).setUpClass()
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Time Off with no validation for approval',
            'time_type': 'leave',
            'requires_allocation': 'yes',
            'allocation_validation_type': 'no',
        })
        cls.department = cls.env['hr.department'].create({
            'name': 'Test Department',
        })
        cls.category_tag = cls.env['hr.employee.category'].create({
            'name': 'Test category'
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'My Employee',
            'company_id': cls.company.id,
            'department_id': cls.department.id,
            'category_ids': [(4, cls.category_tag.id)],
        })

    def test_allocation_whole_company(self):
        company_allocation = self.env['hr.leave.allocation'].create({
            'name': 'Bank Holiday',
            'holiday_type': 'company',
            'mode_company_id': self.company.id,
            'holiday_status_id': self.leave_type.id,
            'number_of_days': 2,
            'allocation_type': 'regular',
        })

        company_allocation.action_validate()

        num_of_allocations = self.env['hr.leave.allocation'].search_count([('employee_id', '=', self.employee.id), ('multi_employee', '=', False)])
        self.assertEqual(num_of_allocations, 1)

    def test_allocation_multi_employee(self):
        employee_allocation = self.env['hr.leave.allocation'].create({
            'name': 'Bank Holiday',
            'holiday_type': 'employee',
            'employee_ids': [(4, self.employee.id), (4, self.employee_emp.id)],
            'employee_id': self.employee.id,
            'holiday_status_id': self.leave_type.id,
            'number_of_days': 2,
            'allocation_type': 'regular',
        })

        employee_allocation.action_validate()

        num_of_allocations = self.env['hr.leave.allocation'].search_count([('employee_id', '=', self.employee.id), ('multi_employee', '=', False), ('parent_id', '!=', False)])
        self.assertEqual(num_of_allocations, 1)

    def test_allocation_department(self):
        department_allocation = self.env['hr.leave.allocation'].create({
            'name': 'Bank Holiday',
            'holiday_type': 'department',
            'department_id': self.department.id,
            'holiday_status_id': self.leave_type.id,
            'number_of_days': 2,
            'allocation_type': 'regular',
        })

        department_allocation.action_validate()

        num_of_allocations = self.env['hr.leave.allocation'].search_count([('employee_id', '=', self.employee.id), ('multi_employee', '=', False)])
        self.assertEqual(num_of_allocations, 1)

    def test_allocation_category(self):
        category_allocation = self.env['hr.leave.allocation'].create({
            'name': 'Bank Holiday',
            'holiday_type': 'category',
            'category_id': self.category_tag.id,
            'holiday_status_id': self.leave_type.id,
            'number_of_days': 2,
            'allocation_type': 'regular',
        })

        category_allocation.action_validate()

        num_of_allocations = self.env['hr.leave.allocation'].search_count([('employee_id', '=', self.employee.id), ('multi_employee', '=', False)])
        self.assertEqual(num_of_allocations, 1)
