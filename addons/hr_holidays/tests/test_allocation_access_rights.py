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

        cls.lt_validation_hr = cls.env['hr.work.entry.type'].create({
            'name': 'Validation = HR',
            'code': 'Validation = HR',
            'allocation_validation_type': 'hr',
            'requires_allocation': True,
            'employee_requests': True,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

        cls.lt_validation_manager = cls.env['hr.work.entry.type'].create({
            'name': 'Validation = manager',
            'code': 'Validation = manager',
            'allocation_validation_type': 'manager',
            'requires_allocation': True,
            'employee_requests': True,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

        cls.lt_allocation_no_validation = cls.env['hr.work.entry.type'].create({
            'name': 'Validation = user',
            'code': 'Validation = user',
            'allocation_validation_type': 'no_validation',
            'requires_allocation': True,
            'employee_requests': True,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

        cls.lt_validation_both = cls.env['hr.work.entry.type'].create({
            'name': 'Validation = both',
            'code': 'Validation = both',
            'allocation_validation_type': 'both',
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
        return self.env['hr.leave.allocation'].with_user(user).create(values)


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestAccessRightsSimpleUser(TestAllocationRights):

    def test_simple_user_request_allocation(self):
        """ A simple user can request an allocation but not approve it """
        values = {
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.lt_validation_manager.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        with self.assertRaises(UserError):
            allocation.action_approve()

    def test_simple_user_request_allocation_no_validation(self):
        """ A simple user can request and automatically validate an allocation with no validation """
        values = {
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.lt_allocation_no_validation.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        self.assertEqual(allocation.state, 'validate', "It should be validated")

    def test_simple_user_request_allocation_no_validation_other(self):
        """ A simple user cannot request an other user's allocation with no validation """
        values = {
            'employee_id': self.employee_hruser.id,
            'work_entry_type_id': self.lt_allocation_no_validation.id,
        }
        with self.assertRaises(AccessError):
            self.request_allocation(self.user_employee.id, values)

    def test_simple_user_reset_to_draft(self):
        """ A simple user can reset to draft only his own allocation """
        values = {
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.lt_validation_manager.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        self.assertEqual(allocation.state, 'confirm', "The allocation should be in 'confirm' state")


@tagged('at_install', '-post_install')  # LEGACY at_install
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
            'work_entry_type_id': self.lt_validation_manager.id,
        }
        with self.assertRaises(AccessError):
            self.request_allocation(self.user_employee.id, values)  # user is not the employee's manager

    def test_manager_approve_request_allocation(self):
        """ A manager can request and approve an allocation for managed employees """
        values = {
            'employee_id': self.managed_employee.id,
            'work_entry_type_id': self.lt_validation_manager.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        allocation.action_approve()
        self.assertEqual(allocation.state, 'validate', "The allocation should be validated")

    def test_manager_refuse_request_allocation(self):
        """ A manager can request and refuse an allocation for managed employees """
        values = {
            'employee_id': self.managed_employee.id,
            'work_entry_type_id': self.lt_validation_manager.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        allocation.action_refuse()
        self.assertEqual(allocation.state, 'refuse', "The allocation should be validated")

    def test_manager_approve_own(self):
        """ A manager cannot approve his own allocation """
        values = {
            'employee_id': self.user_employee.employee_id.id,
            'work_entry_type_id': self.lt_validation_manager.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        with self.assertRaises(UserError):
            allocation.action_approve()


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestAccessRightsHolidayUser(TestAllocationRights):

    def test_holiday_user_request_allocation(self):
        """ A holiday user can request and approve an allocation for any internal employee """
        values = {
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.lt_validation_hr.id,
        }
        allocation = self.request_allocation(self.user_hruser.id, values)
        allocation.action_approve()
        self.assertEqual(allocation.state, 'validate', "It should have been validated")

    def test_holiday_user_cannot_approve_own(self):
        """ A holiday user cannot approve his own allocation """
        values = {
            'employee_id': self.employee_hruser.id,
            'work_entry_type_id': self.lt_validation_manager.id,
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
            'work_entry_type_id': self.lt_validation_hr.id,
        }
        allocation = self.request_allocation(self.user_hruser.id, values).with_company(self.external_company.id)
        self.assertEqual(allocation.can_validate, True)
        self.assertEqual(allocation.can_approve, False)

        self.assertEqual(allocation.state, 'confirm')
        allocation.action_approve()
        self.assertEqual(allocation.state, 'validate')


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestAccessRightsHolidayManager(TestAllocationRights):

    def test_holiday_manager_can_approve_own(self):
        """ A holiday manager can approve his own allocation """
        values = {
            'employee_id': self.employee_hrmanager.id,
            'work_entry_type_id': self.lt_validation_manager.id,
        }
        allocation = self.request_allocation(self.user_hrmanager.id, values)
        allocation.action_approve()
        self.assertEqual(allocation.state, 'validate', "It should have been validated")

    def test_holiday_manager_refuse_validated(self):
        """ A holiday manager can refuse a validated allocation """
        values = {
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.lt_validation_manager.id,
        }
        allocation = self.request_allocation(self.user_hrmanager.id, values)
        allocation.action_approve()
        self.assertEqual(allocation.state, 'validate', "It should have been validated")
        allocation.action_refuse()
        self.assertEqual(allocation.state, 'refuse', "It should have been refused")


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestAccessRightsHrResponsible(TestAllocationRights):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = cls.env.ref('hr_holidays.group_hr_holidays_employee') + cls.env.ref('hr.group_hr_user')
        cls.user_responsible.group_ids |= groups
        cls.employee_emp.hr_responsible_id = cls.user_responsible

    def test_hr_responsible_approve_refuse_allocation(self):
        """
            The employee's HR responsible should be able to approve and refuse an allocation whose
            time off type is validated "By HR Responsible", even without any officer right on
            Time Off
        """
        values = {
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.lt_validation_hr.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        allocation.with_user(self.user_responsible).action_refuse()
        self.assertEqual(allocation.state, 'refuse')

        allocation = self.request_allocation(self.user_employee.id, values)
        allocation.with_user(self.user_responsible).action_approve()
        self.assertEqual(allocation.state, 'validate')

    def test_hr_responsible_first_approval_double_validation_allocation(self):
        """
            On a "By HR Responsible and Time Off Approver" allocation type, the HR responsible
            can give the first approval (and refuse), but the final validation still requires
            a Time Off Officer/Approver
        """
        values = {
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.lt_validation_both.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        allocation.with_user(self.user_responsible).action_approve()
        self.assertEqual(allocation.state, 'validate1')
        with self.assertRaises(UserError):
            allocation.with_user(self.user_responsible).action_approve()
        allocation.with_user(self.user_hrmanager.id).action_approve()
        self.assertEqual(allocation.state, 'validate')

    def test_hr_responsible_refuse_double_validation_allocation(self):
        """
            On a "By HR Responsible and Time Off Approver" allocation type, the HR responsible
            can refuse the allocation, both before and after giving the first approval.
        """
        values = {
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.lt_validation_both.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        allocation.with_user(self.user_responsible).action_refuse()
        self.assertEqual(allocation.state, 'refuse')

        # Check that refusing after giving the first approval also works
        allocation = self.request_allocation(self.user_employee.id, values)
        allocation.with_user(self.user_responsible).action_approve()
        self.assertEqual(allocation.state, 'validate1')
        allocation.with_user(self.user_responsible).action_refuse()
        self.assertEqual(allocation.state, 'refuse')

    def test_hr_responsible_cannot_approve_manager_validation_allocation(self):
        """ The HR responsible has no special right on an allocation validated by the Time Off Approver only """
        values = {
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.lt_validation_manager.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        with self.assertRaises(UserError):
            allocation.with_user(self.user_responsible).action_approve()

    def test_hr_responsible_of_another_employee_cannot_approve_allocation(self):
        """ Being HR responsible of one employee doesn't grant any right on another employee's allocations """
        # hr_responsible_id is required, so re-assign it rather than clear it
        self.employee_emp.hr_responsible_id = self.employee_hruser.user_id
        values = {
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.lt_validation_hr.id,
        }
        allocation = self.request_allocation(self.user_employee.id, values)
        with self.assertRaises(AccessError):
            allocation.with_user(self.user_responsible).action_approve()
