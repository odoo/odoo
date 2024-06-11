from datetime import date

from freezegun import freeze_time

from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged, users

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

        cls.leave_type_paid = cls.env['hr.leave.type'].create({
            'name': 'Paid Time Off',
            'requires_allocation': 'yes',
            'allocation_validation_type': 'no',
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

    def test_allocation_request(self):
        self.leave_type.write({
            'name': 'Custom Time Off Test',
            'allocation_validation_type': 'officer'
        })

        employee_allocation = self.env['hr.leave.allocation'].create({
            'holiday_type': 'employee',
            'employee_id': self.employee.id,
            'holiday_status_id': self.leave_type.id,
            'allocation_type': 'regular',
        })

        with Form(employee_allocation.with_context(is_employee_allocation=True), 'hr_holidays.hr_leave_allocation_view_form_dashboard') as allocation:
            allocation.number_of_days_display = 10
            employee_allocation = allocation.save()

        self.assertEqual(employee_allocation.private_name, "Custom Time Off Test allocation request (10.0 day)")

    def test_allowed_change_allocation(self):
        allocation = self.env['hr.leave.allocation'].create({
            'name': 'Initial Allocation',
            'holiday_status_id': self.leave_type_paid.id,
            'number_of_days': 20,
            'employee_id': self.employee.id,
            'date_from': date(2024, 1, 1),
        })
        allocation.action_validate()

        leave_request = self.env['hr.leave'].create({
            'name': 'Leave Request',
            'holiday_status_id': self.leave_type_paid.id,
            'request_date_from': date(2024, 1, 5),
            'request_date_to': date(2024, 1, 10),
            'employee_id': self.employee.id,
        })
        leave_request.action_approve()
        allocation.write({'number_of_days_display': 14, 'number_of_days': 14})
        self.assertEqual(allocation.number_of_days_display, 14)

        with self.assertRaises(ValidationError):
            allocation.write({'number_of_days_display': 2, 'number_of_days': 2})

    def test_disallowed_change_allocation_with_overlapping_allocations(self):
        # Creating the first allocation
        allocation_one = self.env['hr.leave.allocation'].create({
            'name': 'First Allocation',
            'holiday_status_id': self.leave_type_paid.id,
            'number_of_days': 5,
            'employee_id': self.employee.id,
            'date_from': date(2024, 1, 1),
            'date_to': date(2024, 1, 30),
        })
        allocation_one.action_validate()

        # Creating the second overlapping allocation
        allocation_two = self.env['hr.leave.allocation'].create({
            'name': 'Second Half Allocation',
            'holiday_status_id': self.leave_type_paid.id,
            'number_of_days': 5,
            'employee_id': self.employee.id,
            'date_from': date(2024, 1, 20),
            'date_to': date(2024, 2, 20),
        })
        allocation_two.action_validate()

        # Creating a leave request consuming days from both allocations
        leave_request = self.env['hr.leave'].create({
            'name': 'Leave Request Spanning Allocations',
            'holiday_status_id': self.leave_type_paid.id,
            'request_date_from': date(2024, 1, 25),
            'request_date_to': date(2024, 2, 5),
            'employee_id': self.employee.id,
        })
        leave_request.action_approve()

        with self.assertRaises(ValidationError):
            allocation_one.write({'number_of_days_display': 2, 'number_of_days': 2})

        allocation_one.write({'number_of_days_display': 3, 'number_of_days': 3})

    @users('admin')
    @freeze_time('2024-03-25')
    def test_allocation_dropdown_after_period(self):
        """
        Test when having two allocations of the same type with different
        time range and submitting a request will the allocations be
        shown correctly in the dropdown menu or not
        :return:
        """
        leave_type = self.env.ref('hr_holidays.holiday_status_comp')
        allocation = self.env['hr.leave.allocation'].sudo().create({
            'name': 'Alloc',
            'employee_id': self.employee.id,
            'holiday_status_id': leave_type.id,
            'number_of_days': 3,
            'allocation_type': 'regular',
            'date_from': date(2024, 1, 1),
            'date_to': date(2024, 4, 30)
        })
        allocation.action_validate()

        second_allocation = self.env['hr.leave.allocation'].sudo().create({
            'name': 'Alloc2',
            'employee_id': self.employee.id,
            'holiday_status_id': leave_type.id,
            'number_of_days': 9,
            'allocation_type': 'regular',
            'date_from': date(2024, 5, 1),
            'date_to': date(2024, 12, 31)
        })
        second_allocation.action_validate()
        result = self.env['hr.leave.type'].with_context(
            employee_id=self.employee.id,
            default_date_from='2024-08-18 06:00:00',
            default_date_to='2024-08-18 15:00:00'
        ).name_search(args=[['id', '=', leave_type.id]])
        self.assertEqual(result[0][1], 'Compensatory Days (72 remaining out of 72 hours)')
