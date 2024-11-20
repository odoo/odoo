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
            'allocation_validation_type': 'no_validation',
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
            'allocation_validation_type': 'no_validation',
        })

        cls.calendar_35h = cls.env['resource.calendar'].create({
            'name': 'Calendar - 35H',
            'company_id': cls.company.id,
            'attendance_ids': [(5, 0, 0),
                    (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                    (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'})
                ]
        })

    def test_allocation_whole_company(self):
        company_allocation = self.env['hr.leave.allocation.generate.multi.wizard'].create({
            'name': 'Bank Holiday',
            'allocation_mode': 'company',
            'company_id': self.company.id,
            'holiday_status_id': self.leave_type.id,
            'duration': 2,
            'allocation_type': 'regular',
        })

        company_allocation.action_generate_allocations()

        num_of_allocations = self.env['hr.leave.allocation'].search_count([('employee_id', '=', self.employee.id)])
        self.assertEqual(num_of_allocations, 1)

    def test_allocation_multi_employee(self):
        employee_allocation = self.env['hr.leave.allocation.generate.multi.wizard'].create({
            'name': 'Bank Holiday',
            'allocation_mode': 'employee',
            'employee_ids': [(4, self.employee.id), (4, self.employee_emp.id)],
            'holiday_status_id': self.leave_type.id,
            'duration': 2,
            'allocation_type': 'regular',
        })

        employee_allocation.action_generate_allocations()

        num_of_allocations = self.env['hr.leave.allocation'].search_count([('employee_id', '=', self.employee.id)])
        self.assertEqual(num_of_allocations, 1)

    def test_allocation_department(self):
        department_allocation = self.env['hr.leave.allocation.generate.multi.wizard'].create({
            'name': 'Bank Holiday',
            'allocation_mode': 'department',
            'department_id': self.department.id,
            'holiday_status_id': self.leave_type.id,
            'duration': 2,
            'allocation_type': 'regular',
        })

        department_allocation.action_generate_allocations()

        num_of_allocations = self.env['hr.leave.allocation'].search_count([('employee_id', '=', self.employee.id)])
        self.assertEqual(num_of_allocations, 1)

    def test_allocation_category(self):
        category_allocation = self.env['hr.leave.allocation.generate.multi.wizard'].create({
            'name': 'Bank Holiday',
            'allocation_mode': 'category',
            'category_id': self.category_tag.id,
            'holiday_status_id': self.leave_type.id,
            'duration': 2,
            'allocation_type': 'regular',
        })

        category_allocation.action_generate_allocations()

        num_of_allocations = self.env['hr.leave.allocation'].search_count([('employee_id', '=', self.employee.id)])
        self.assertEqual(num_of_allocations, 1)

    def test_allocation_request_day(self):
        self.leave_type.write({
            'name': 'Custom Time Off Test',
            'allocation_validation_type': 'hr'
        })

        employee_allocation = self.env['hr.leave.allocation'].create({
            'employee_id': self.employee.id,
            'holiday_status_id': self.leave_type.id,
            'allocation_type': 'regular',
        })

        with Form(employee_allocation.with_context(is_employee_allocation=True), 'hr_holidays.hr_leave_allocation_view_form_dashboard') as allocation:
            allocation.number_of_days_display = 10
            employee_allocation = allocation.save()

        self.assertEqual(employee_allocation.name, "Custom Time Off Test (10.0 day(s))")

    def test_allocation_request_half_days(self):
        self.leave_type.write({
            'name': 'Custom Time Off Test',
            'allocation_validation_type': 'hr'
        })

        employee_allocation = self.env['hr.leave.allocation'].create({
            'employee_id': self.employee.id,
            'holiday_status_id': self.leave_type.id,
            'allocation_type': 'regular',
            'type_request_unit': 'half_day',
        })

        with Form(employee_allocation.with_context(is_employee_allocation=True), 'hr_holidays.hr_leave_allocation_view_form_dashboard') as allocation:
            allocation.number_of_days_display = 10
            employee_allocation = allocation.save()

        self.assertEqual(employee_allocation.name, "Custom Time Off Test (10.0 day(s))")

    def change_allocation_type_day(self):
        self.leave_type.write({
            'name': 'Custom Time Off Test',
            'allocation_validation_type': 'hr'
        })

        employee_allocation = self.env['hr.leave.allocation'].create({
            'holiday_type': 'employee',
            'employee_id': self.employee.id,
            'holiday_status_id': self.leave_type.id,
            'allocation_type': 'regular',
        })

        with Form(employee_allocation.with_context(is_employee_allocation=True), 'hr_holidays.hr_leave_allocation_view_form_dashboard') as allocation:
            allocation.allocation_type = 'extra'
            allocation.allocation_type = 'regular'
            employee_allocation = allocation.save()

        self.assertEqual(employee_allocation.number_of_days, 1.0)

    def test_allocation_type_hours_with_resource_calendar(self):
        self.leave_type.request_unit = 'hour'
        self.employee.resource_calendar_id = self.calendar_35h

        hour_type_allocation = self.env['hr.leave.allocation.generate.multi.wizard'].create({
            'name': 'Hours Allocation',
            'allocation_mode': 'employee',
            'employee_ids': [(4, self.employee.id), (4, self.employee_emp.id)],
            'holiday_status_id': self.leave_type.id,
            'duration': 10,
            'allocation_type': 'regular',
        })

        self.assertEqual(self.employee.resource_calendar_id.hours_per_day, 7.0)
        self.assertEqual(self.employee_emp.resource_calendar_id.hours_per_day, 8.0)

        hour_type_allocation.action_generate_allocations()

        # Find allocations created for individual employees
        employee_allocation = self.env['hr.leave.allocation'].search([
            ('employee_id', '=', self.employee.id),
        ])
        employee_emp_allocation = self.env['hr.leave.allocation'].search([
            ('employee_id', '=', self.employee_emp.id),
        ])

        self.assertEqual(employee_allocation.number_of_hours_display, 10)
        self.assertEqual(employee_emp_allocation.number_of_hours_display, 10)

    def change_allocation_type_hours(self):
        self.leave_type.write({
            'name': 'Custom Time Off Test',
            'allocation_validation_type': 'hr'
        })

        employee_allocation = self.env['hr.leave.allocation'].create({
            'holiday_type': 'employee',
            'employee_id': self.employee.id,
            'holiday_status_id': self.leave_type.id,
            'allocation_type': 'regular',
            'type_request_unit': 'hour',
        })

        with Form(employee_allocation.with_context(is_employee_allocation=True), 'hr_holidays.hr_leave_allocation_view_form_dashboard') as allocation:
            allocation.allocation_type = 'extra'
            allocation.allocation_type = 'regular'
            employee_allocation = allocation.save()

        self.assertEqual(employee_allocation.number_of_days, 1.0)

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
        self.assertEqual(result[0][1], 'Compensatory Days (9 remaining out of 9 days)')

    def test_allocation_hourly_leave_type(self):
        """
        Make sure that the number of hours is correctly set on the allocation for an hourly leave type
        for an employee who works some other schedule than the default 8 hours per day.
        """
        employee = self.env['hr.employee'].create({
            'name': 'My Employee',
            'company_id': self.company.id,
            'resource_calendar_id': self.calendar_35h.id,
        })

        leave_type = self.env['hr.leave.type'].create({
            'name': 'Hourly Leave Type',
            'time_type': 'leave',
            'requires_allocation': 'yes',
            'allocation_validation_type': 'no_validation',
            'request_unit': 'hour',
        })

        with Form(self.env['hr.leave.allocation']) as allocation_form:
            allocation_form.allocation_type = 'regular'
            allocation_form.employee_id = employee
            allocation_form.holiday_status_id = leave_type
            allocation_form.number_of_hours_display = 10
            allocation = allocation_form.save()

        self.assertEqual(allocation.number_of_hours_display, 10.0)
