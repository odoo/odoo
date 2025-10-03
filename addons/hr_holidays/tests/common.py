# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import common


class TestHrHolidaysCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestHrHolidaysCommon, cls).setUpClass()
        cls.env.user.tz = 'Europe/Brussels'
        cls.env.user.company_id.resource_calendar_id.tz = "Europe/Brussels"

        cls.company = cls.env['res.company'].create({'name': 'Test company'})
        cls.env.user.company_id = cls.company

        # Test users to use through the various tests
        cls.user_hruser = mail_new_test_user(cls.env, login='armande', groups='base.group_user,hr_holidays.group_hr_holidays_user')
        cls.user_hruser_id = cls.user_hruser.id

        cls.user_hrmanager = mail_new_test_user(cls.env, login='bastien', groups='base.group_user,hr_holidays.group_hr_holidays_manager')
        cls.user_hrmanager_id = cls.user_hrmanager.id
        cls.user_hrmanager.tz = 'Europe/Brussels'

        cls.user_employee = mail_new_test_user(cls.env, login='enguerran', password='enguerran', groups='base.group_user')
        cls.user_employee_id = cls.user_employee.id

        # Hr Data
        Department = cls.env['hr.department'].with_context(tracking_disable=True)

        cls.hr_dept = Department.create({
            'name': 'Human Resources',
        })
        cls.rd_dept = Department.create({
            'name': 'Research and devlopment',
        })

        cls.employee_emp = cls.env['hr.employee'].create({
            'name': 'David Employee',
            'user_id': cls.user_employee_id,
            'department_id': cls.rd_dept.id,
        })
        cls.employee_emp_id = cls.employee_emp.id

        cls.employee_hruser = cls.env['hr.employee'].create({
            'name': 'Armande HrUser',
            'user_id': cls.user_hruser_id,
            'department_id': cls.rd_dept.id,
        })
        cls.employee_hruser_id = cls.employee_hruser.id

        cls.employee_hrmanager = cls.env['hr.employee'].create({
            'name': 'Bastien HrManager',
            'user_id': cls.user_hrmanager_id,
            'department_id': cls.hr_dept.id,
            'parent_id': cls.employee_hruser_id,
        })
        cls.employee_hrmanager_id = cls.employee_hrmanager.id

        cls.rd_dept.write({'manager_id': cls.employee_hruser_id})
        cls.hours_per_day = cls.employee_emp.resource_id.calendar_id.hours_per_day or 8

    def assert_virtual_leaves_equal(self, leave_type, value, employee, date=None, digits=False):
        allocation_data = leave_type.get_allocation_data(employee, date)
        if not date:
            date = fields.Date.today()
        if digits:
            self.assertAlmostEqual(allocation_data[employee][0][1]['remaining_leaves'], value,
                digits, f"Virtual leaves for date '{date}' are incorrect.")
        else:
            self.assertEqual(allocation_data[employee][0][1]['remaining_leaves'],
                value, f"Virtual leaves for date '{date}' are incorrect.")

    def _take_leave_and_validate(self, employee, leave_type, date_from, date_to):
        leave = self.env['hr.leave'].create({
            'name': 'Leave',
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': date_from,
            'request_date_to': date_to,
        })
        leave.action_validate()
        return leave

    def _create_test_allocation(self, leave_type, date_from, employee, accrual_plan=None, number_of_days=None, date_to=None):
        return self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'Accrual allocation for employee',
            'allocation_type': 'accrual' if accrual_plan else 'regular',
            'accrual_plan_id': accrual_plan.id if accrual_plan else None,
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'number_of_days': number_of_days if number_of_days is not None else 0,
            'date_from': date_from,
            'date_to': date_to,
        })
