# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon
from odoo.tests import tagged

from odoo.exceptions import AccessError, UserError
import time


class TestAllocationRights(TestHrHolidaysCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.rd_dept.manager_id = False
        cls.hr_dept.manager_id = False
        cls.employee_emp.parent_id = False
        cls.employee_emp.leave_manager_id = False

        cls.lt_validation_hr = cls.env['hr.time.type'].create({
            'name': 'Validation = HR',
            'code': 'Validation = HR',
            'allocation_validation_type': 'hr',
            'requires_allocation': True,
            'employee_requests': True,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

        cls.lt_validation_manager = cls.env['hr.time.type'].create({
            'name': 'Validation = manager',
            'code': 'Validation = manager',
            'allocation_validation_type': 'manager',
            'requires_allocation': True,
            'employee_requests': True,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

        cls.lt_allocation_no_validation = cls.env['hr.time.type'].create({
            'name': 'Validation = user',
            'code': 'Validation = user',
            'allocation_validation_type': 'no_validation',
            'requires_allocation': True,
            'employee_requests': True,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

    def request_allocation(self, user, values={}):
        values = dict(values, **{
            'name': 'Allocation',
            'number_of_days': 1,
            'date_from': time.strftime('%Y-01-01'),
            'date_to': time.strftime('%Y-12-31'),
        })
        return self.env['hr.leave.allocation'].with_user(user).with_context(allocation_skip_auto_approve=True).create(values)


class TestAccessRightsSimpleUser(TestAllocationRights):

    def test_simple_user_request_allocation(self):
        """ A simple user can request an allocation but not approve it """
        values = {
            'employee_id': self.employee_emp.id,
            'time_type_id': self.lt_validation_manager.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        with self.assertRaises(UserError):
            allocation.action_approve()

    def test_simple_user_request_allocation_no_validation(self):
        """ A simple user can request and automatically validate an allocation with no validation """
        values = {
            'employee_id': self.employee_emp.id,
            'time_type_id': self.lt_allocation_no_validation.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        self.assertEqual(allocation.state, 'validate', "It should be validated")

    def test_simple_user_request_allocation_no_validation_other(self):
        """ A simple user cannot request an other user's allocation with no validation """
        values = {
            'employee_id': self.employee_hruser.id,
            'time_type_id': self.lt_allocation_no_validation.id,
        }
        with self.assertRaises(AccessError):
            self.request_allocation(self.user_employee.id, values)

    def test_allocation_approval_flags_depend_on_user(self):
        """ The approval flags of an allocation are computed for the current user """
        lt_validation_both = self.env['hr.time.type'].create({
            'name': 'Validation = both',
            'code': 'Validation = both',
            'allocation_validation_type': 'both',
            'requires_allocation': True,
            'employee_requests': True,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })
        allocation = self.request_allocation(self.user_employee.id, {
            'employee_id': self.employee_emp.id,
            'time_type_id': lt_validation_both.id,
        })
        users = (self.user_hrmanager, self.user_employee)
        for field_name in ('can_approve', 'can_validate', 'can_refuse'):
            values = []
            for user in users:
                allocation.invalidate_recordset([field_name])
                values.append(allocation.with_user(user)[field_name])
            self.assertEqual(values, [True, False], field_name)
            allocation.invalidate_recordset([field_name])
            self.assertEqual([allocation.with_user(user)[field_name] for user in users], values, field_name)

    def test_allocation_request_approval_activity(self):
        """ The approval activity of an allocation follows the allocation validation type """
        time_type = self.env['hr.time.type'].create({
            'name': 'Allocation by HR, time off without validation',
            'code': 'Allocation by HR',
            'allocation_validation_type': 'hr',
            'leave_validation_type': 'no_validation',
            'requires_allocation': True,
            'employee_requests': True,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })
        self.employee_emp.hr_responsible_id = self.user_hrmanager
        allocation = self.request_allocation(self.user_employee.id, {
            'employee_id': self.employee_emp.id,
            'time_type_id': time_type.id,
        })
        self.assertEqual(allocation.state, 'confirm')
        self.assertEqual(
            allocation.activity_ids.activity_type_id,
            self.env.ref('hr_holidays.mail_act_leave_allocation_approval'),
        )
        self.assertEqual(allocation.activity_ids.user_id, self.user_hrmanager)

    def test_simple_user_reset_to_draft(self):
        """ A simple user can reset to draft only his own allocation """
        values = {
            'employee_id': self.employee_emp.id,
            'time_type_id': self.lt_validation_manager.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        self.assertEqual(allocation.state, 'confirm', "The allocation should be in 'confirm' state")


class TestAccessRightsEmployeeManager(TestAllocationRights):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.managed_employee = cls.env['hr.employee'].create({
            'name': 'Jolly Jumper',
            'leave_manager_id': cls.user_employee.id,
        })

    def test_manager_request_allocation_other(self):
        """ A manager cannot request and approve an allocation for employees he doesn't manage """
        values = {
            'employee_id': self.employee_hruser.id,
            'time_type_id': self.lt_validation_manager.id,
        }
        with self.assertRaises(AccessError):
            self.request_allocation(self.user_employee.id, values)  # user is not the employee's manager

    def test_manager_approve_request_allocation(self):
        """ A manager can request and approve an allocation for managed employees """
        values = {
            'employee_id': self.managed_employee.id,
            'time_type_id': self.lt_validation_manager.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        allocation.action_approve()
        self.assertEqual(allocation.state, 'validate', "The allocation should be validated")

    def test_manager_refuse_request_allocation(self):
        """ A manager can request and refuse an allocation for managed employees """
        values = {
            'employee_id': self.managed_employee.id,
            'time_type_id': self.lt_validation_manager.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        allocation.action_refuse()
        self.assertEqual(allocation.state, 'refuse', "The allocation should be validated")

    def test_manager_approve_own(self):
        """ A manager cannot approve his own allocation """
        values = {
            'employee_id': self.user_employee.employee_id.id,
            'time_type_id': self.lt_validation_manager.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        with self.assertRaises(UserError):
            allocation.action_approve()


class TestAccessRightsHolidayUser(TestAllocationRights):

    def test_holiday_user_request_allocation(self):
        """ A holiday user can request and approve an allocation for any internal employee """
        values = {
            'employee_id': self.employee_emp.id,
            'time_type_id': self.lt_validation_hr.id,
        }
        allocation = self.request_allocation(self.user_hruser.id, values)
        allocation.action_approve()
        self.assertEqual(allocation.state, 'validate', "It should have been validated")

    def test_holiday_user_cannot_approve_own(self):
        """ A holiday user cannot approve his own allocation """
        values = {
            'employee_id': self.employee_hruser.id,
            'time_type_id': self.lt_validation_manager.id,
        }
        allocation = self.request_allocation(self.user_hruser.id, values)
        with self.assertRaises(UserError):
            allocation.action_approve()

    def test_holiday_user_cannot_approve_external_company(self):
        """A holidy user can validate but not approve allocations for employees in external company"""

        self.user_hruser.write({
        'company_ids': [(6, 0, [self.company.id, self.external_company.id])],
        })

        values = {
            'employee_id': self.employee_external.id,
            'time_type_id': self.lt_validation_hr.id,
        }
        allocation = self.request_allocation(self.user_hruser.id, values).with_company(self.external_company.id)
        self.assertEqual(allocation.can_validate, True)
        self.assertEqual(allocation.can_approve, False)

        self.assertEqual(allocation.state, 'confirm')
        allocation.action_approve()
        self.assertEqual(allocation.state, 'validate')


class TestAccessRightsHolidayManager(TestAllocationRights):

    def test_holiday_manager_can_approve_own(self):
        """ A holiday manager can approve his own allocation """
        values = {
            'employee_id': self.employee_hrmanager.id,
            'time_type_id': self.lt_validation_manager.id,
        }
        allocation = self.request_allocation(self.user_hrmanager.id, values)
        allocation.action_approve()
        self.assertEqual(allocation.state, 'validate', "It should have been validated")

    def test_holiday_manager_refuse_validated(self):
        """ A holiday manager can refuse a validated allocation """
        values = {
            'employee_id': self.employee_emp.id,
            'time_type_id': self.lt_validation_manager.id,
        }
        allocation = self.request_allocation(self.user_hrmanager.id, values)
        allocation.action_approve()
        self.assertEqual(allocation.state, 'validate', "It should have been validated")
        allocation.action_refuse()
        self.assertEqual(allocation.state, 'refuse', "It should have been refused")
