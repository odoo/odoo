# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tests
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon
from odoo.exceptions import AccessError, UserError


@tests.tagged('access_rights', 'post_install', '-at_install')
class TestAllocationRights(TestHrHolidaysCommon):

    def setUp(self):
        super().setUp()
        self.rd_dept.manager_id = False
        self.hr_dept.manager_id = False
        self.employee_emp.parent_id = False
        self.employee_emp.leave_manager_id = False

        self.lt_validation_hr = self.env['hr.leave.type'].create({
            'name': 'Validation = HR',
            'allocation_validation_type': 'hr',
            'allocation_type': 'fixed_allocation',
            'validity_start': False,
        })

        self.lt_validation_manager = self.env['hr.leave.type'].create({
            'name': 'Validation = manager',
            'allocation_validation_type': 'manager',
            'allocation_type': 'fixed_allocation',
            'validity_start': False,
        })

        self.lt_validation_both = self.env['hr.leave.type'].create({
            'name': 'Validation = both',
            'allocation_validation_type': 'both',
            'allocation_type': 'fixed_allocation',
            'validity_start': False,
        })

    def request_allocation(self, user, values={}):
        values = dict(values, **{
            'name': 'Allocation',
            'number_of_days': 1,
        })
        return self.env['hr.leave.allocation'].with_user(user).create(values)


class TestAccessRightsSimpleUser(TestAllocationRights):

    def test_simple_user_request_allocation(self):
        """ A simple user can request an allocation but not approve it """
        values = {
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.lt_validation_hr.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        with self.assertRaises(UserError):
            allocation.action_approve()

    def test_simple_user_request_fixed_allocation(self):
        """ A simple user cannot request an allocation if set by HR """
        self.lt_validation_hr.allocation_type = 'fixed'
        values = {
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.lt_validation_hr.id,
        }
        with self.assertRaises(AccessError):
            self.request_allocation(self.user_employee.id, values)

    def test_simple_user_reset_to_draft(self):
        """ A simple user can reset to draft only his own allocation """
        values = {
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.lt_validation_hr.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        self.assertEqual(allocation.state, 'confirm')
        allocation.action_draft()
        self.assertEqual(allocation.state, 'draft', "It should be reset to draft state")


class TestAccessRightsEmployeeManager(TestAllocationRights):

    def setUp(self):
        super().setUp()
        self.managed_employee = self.env['hr.employee'].create({
            'name': 'Jolly Jumper',
            'leave_manager_id': self.user_employee.id,
        })

    def test_manager_request_allocation_other(self):
        """ A manager cannot request and approve an allocation for employees he doesn't manage """
        values = {
            'employee_id': self.employee_hruser.id,
            'holiday_status_id': self.lt_validation_manager.id,
        }
        with self.assertRaises(AccessError):
            self.request_allocation(self.user_employee.id, values)  # user is not the employee's manager

    def test_manager_approve_request_allocation(self):
        """ A manager can request and approve an allocation for managed employees """
        values = {
            'employee_id': self.managed_employee.id,
            'holiday_status_id': self.lt_validation_manager.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        allocation.action_approve()
        self.assertEqual(allocation.state, 'validate', "The allocation should be validated")

    def test_manager_refuse_request_allocation(self):
        """ A manager can request and refuse an allocation for managed employees """
        values = {
            'employee_id': self.managed_employee.id,
            'holiday_status_id': self.lt_validation_manager.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        allocation.action_refuse()
        self.assertEqual(allocation.state, 'refuse', "The allocation should be validated")

    def test_manager_batch_allocation(self):
        """ A manager cannot create batch allocation """
        values = {
            'holiday_status_id': self.lt_validation_manager.id,
            'holiday_type': 'company',
            'mode_company_id': self.user_employee.company_id.id,
        }
        with self.assertRaises(AccessError):
            self.request_allocation(self.user_employee.id, values)

    def test_manager_approve_own(self):
        """ A manager cannot approve his own allocation """
        values = {
            'employee_id': self.user_employee.employee_id.id,
            'holiday_status_id': self.lt_validation_manager.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        with self.assertRaises(UserError):
            allocation.action_approve()

    def test_manager_only_first_approval(self):
        """ A manager can only do the first approval """
        values = {
            'employee_id': self.managed_employee.id,
            'holiday_status_id': self.lt_validation_both.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        allocation.action_approve()
        with self.assertRaises(UserError):
            allocation.action_validate()


class TestAccessRightsHolidayUser(TestAllocationRights):

    def test_holiday_user_request_allocation(self):
        """ A holiday user can request and approve an allocation for any employee """
        values = {
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.lt_validation_hr.id,
        }
        allocation = self.request_allocation(self.user_hruser.id, values)
        allocation.action_approve()
        self.assertEqual(allocation.state, 'validate', "It should have been validated")

    def test_holiday_user_request_fixed_allocation(self):
        """ A holiday user can request and approve an allocation if set by HR """
        self.lt_validation_hr.allocation_type = 'fixed'
        values = {
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.lt_validation_hr.id,
        }
        allocation = self.request_allocation(self.user_hruser.id, values)
        allocation.action_approve()
        self.assertEqual(allocation.state, 'validate', "It should have been validated")

    def test_holiday_user_both_second_approval(self):
        """ A holiday user can only do the second approval when double validation """
        values = {
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.lt_validation_both.id,
        }
        allocation = self.request_allocation(self.user_hruser.id, values)
        with self.assertRaises(UserError):
            allocation.action_approve()
        allocation.sudo().action_approve()  # First approval by someone else
        allocation.action_validate()
        self.assertEqual(allocation.state, 'validate', "It should have been validated")

    def test_holiday_user_batch_allocation(self):
        """ A holiday user cannot create a batch allocation """
        values = {
            'holiday_status_id': self.lt_validation_hr.id,
            'holiday_type': 'company',
            'mode_company_id': self.user_employee.company_id.id,
        }
        with self.assertRaises(AccessError):
            self.request_allocation(self.user_hruser.id, values)

    def test_holiday_user_cannot_approve_own(self):
        """ A holiday user cannot approve his own allocation """
        values = {
            'employee_id': self.employee_hruser.id,
            'holiday_status_id': self.lt_validation_hr.id,
        }
        allocation = self.request_allocation(self.user_hruser.id, values)
        with self.assertRaises(UserError):
            allocation.action_approve()


class TestAccessRightsHolidayManager(TestAllocationRights):

    def test_holiday_manager_can_approve_own(self):
        """ A holiday manager can approve his own allocation """
        values = {
            'employee_id': self.employee_hrmanager.id,
            'holiday_status_id': self.lt_validation_hr.id,
        }
        allocation = self.request_allocation(self.user_hrmanager.id, values)
        allocation.action_approve()
        self.assertEqual(allocation.state, 'validate', "It should have been validated")

    def test_holiday_manager_both_validation(self):
        """ A holiday manager can perform both validation """
        values = {
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.lt_validation_both.id,
        }
        allocation = self.request_allocation(self.user_hrmanager.id, values)
        allocation.action_approve()
        self.assertEqual(allocation.state, 'validate1', "It should have been validated one time")
        allocation.action_validate()
        self.assertEqual(allocation.state, 'validate', "It should have been completely validated")

    def test_holiday_manager_refuse_validated(self):
        """ A holiday manager can refuse a validated allocation """
        values = {
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.lt_validation_hr.id,
        }
        allocation = self.request_allocation(self.user_hrmanager.id, values)
        allocation.action_approve()
        self.assertEqual(allocation.state, 'validate', "It should have been validated")
        allocation.action_refuse()
        self.assertEqual(allocation.state, 'refuse', "It should have been refused")
