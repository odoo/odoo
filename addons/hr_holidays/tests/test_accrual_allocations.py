# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, time
from dateutil.relativedelta import relativedelta

from odoo import fields

from odoo.tools import mute_logger

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestAccrualAllocations(TestHrHolidaysCommon):
    def setUp(self):
        super(TestAccrualAllocations, self).setUp()

        # Make sure we have the rights to create, validate and delete the leaves, leave types and allocations
        LeaveType = self.env['hr.leave.type'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True)

        self.accrual_type = LeaveType.create({
            'name': 'accrual',
            'allocation_type': 'fixed',
            'validity_start': False,
        })

        self.unpaid_type = LeaveType.create({
            'name': 'unpaid',
            'allocation_type': 'no',
            'unpaid': True,
            'validity_start': False,
        })

        self.set_employee_create_date(self.employee_emp_id, '2010-02-03 00:00:00')
        self.set_employee_create_date(self.employee_hruser_id, '2010-02-03 00:00:00')

    def set_employee_create_date(self, id, newdate):
        """ This method is a hack in order to be able to define/redefine the create_date
            of the employees.
            This is done in SQL because ORM does not allow to write onto the create_date field.
        """
        self.env.cr.execute("""
                       UPDATE
                       hr_employee
                       SET create_date = '%s'
                       WHERE id = %s
                       """ % (newdate, id))

    def test_accrual_base_no_leaves(self):
        """ Test if we can allocate some leaves accrually to an employee """
        alloc = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'Accrual allocation for employee',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'allocation_type': 'accrual',
            'number_of_days': 0,
            'number_per_interval': 1,
            'interval_number': 1,
            'unit_per_interval': 'days',
            'interval_unit': 'weeks',
        })
        alloc.action_approve()
        alloc._update_accrual()

        self.assertEqual(alloc.number_of_days, 1, 'Employee should have been allocated one leave day')

    def test_accrual_base_leaves(self):
        """ Test if the accrual allocation take the unpaid leaves into account when allocating leaves """
        alloc = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'Accrual allocation for employee with leaves',
            'employee_id': self.employee_hruser_id,
            'holiday_status_id': self.accrual_type.id,
            'allocation_type': 'accrual',
            'number_of_days': 0,
            'number_per_interval': 1,
            'interval_number': 1,
            'unit_per_interval': 'days',
            'interval_unit': 'weeks',
        })

        alloc.action_approve()

        employee = self.env['hr.employee'].browse(self.employee_hruser_id)
        # Getting the previous work date
        df = employee.resource_calendar_id.plan_days(-2, fields.Datetime.now()).date()

        leave = self.env['hr.leave'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'Leave for hruser',
            'employee_id': self.employee_hruser_id,
            'holiday_status_id': self.unpaid_type.id,
            'date_from': datetime.combine(df, time(0, 0, 0)),
            'date_to': datetime.combine(df + relativedelta(days=1), time(0, 0, 0)),
            'number_of_days': 1,
        })

        leave.action_approve()

        alloc._update_accrual()

        self.assertEqual(alloc.number_of_days, .8, 'As employee took some unpaid leaves last week, he should be allocated only .8 days')

    def test_accrual_many(self):
        """
            Test different configuration of accrual allocations
        """
        Allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True)

        alloc_0 = Allocation.create({
            'name': '1 day per 2 weeks',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'allocation_type': 'accrual',
            'number_of_days': 0,
            'number_per_interval': 1,
            'interval_number': 2,
            'unit_per_interval': 'days',
            'interval_unit': 'weeks',
        })

        alloc_1 = Allocation.create({
            'name': '4 hours per week',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'allocation_type': 'accrual',
            'number_of_days': 0,
            'number_per_interval': 4,
            'interval_number': 1,
            'unit_per_interval': 'hours',
            'interval_unit': 'weeks',
        })

        alloc_2 = Allocation.create({
            'name': '2 day per 1 month',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'allocation_type': 'accrual',
            'number_of_days': 0,
            'number_per_interval': 2,
            'interval_number': 1,
            'unit_per_interval': 'days',
            'interval_unit': 'months',
        })

        alloc_3 = Allocation.create({
            'name': '20 days per year',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'allocation_type': 'accrual',
            'number_of_days': 0,
            'number_per_interval': 20,
            'interval_number': 1,
            'unit_per_interval': 'days',
            'interval_unit': 'years',
        })

        (alloc_0 | alloc_1 | alloc_2 | alloc_3).action_approve()

        Allocation._update_accrual()

        self.assertEqual(alloc_0.number_of_days, 1)
        self.assertEqual(alloc_1.number_of_days, .5)
        self.assertEqual(alloc_2.number_of_days, 2)
        self.assertEqual(alloc_3.number_of_days, 20)

    def test_accrual_new_employee(self):
        """
            Test if accrual allocation takes into account the creation date
            of an employee
        """
        Allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True)

        self.set_employee_create_date(self.employee_emp_id, fields.Datetime.to_string(fields.Datetime.now()))

        alloc_0 = Allocation.create({
            'name': 'one shot one kill',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'allocation_type': 'accrual',
            'number_of_days': 0,
            'number_per_interval': 1,
            'interval_number': 1,
            'unit_per_interval': 'days',
            'interval_unit': 'weeks',
        })

        alloc_0.action_approve()

        Allocation._update_accrual()

        self.assertEqual(alloc_0.number_of_days, 0, 'Employee is new he should not get any accrual leaves')

    def test_accrual_multi(self):
        """ Test if the cron does not allocate leaves every time it's called but only when necessary """
        alloc = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': '2 days per week',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'allocation_type': 'accrual',
            'number_of_days': 0,
            'number_per_interval': 1,
            'interval_number': 2,
            'unit_per_interval': 'days',
            'interval_unit': 'weeks',
        })
        alloc.action_approve()
        alloc._update_accrual()
        alloc._update_accrual()

        self.assertEqual(alloc.number_of_days, 1, 'Cron only allocates 1 days every two weeks')

    def test_accrual_validation(self):
        """
            Test if cron does not allocate past it's validity date
        """
        Allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True)

        alloc_0 = Allocation.create({
            'name': '20 days per year',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'number_of_days': 0,
            'number_per_interval': 20,
            'interval_number': 1,
            'unit_per_interval': 'days',
            'interval_unit': 'years',
            'date_to': fields.Datetime.from_string('2015-02-03 00:00:00'),
        })

        alloc_0.action_approve()

        Allocation._update_accrual()

        self.assertEqual(alloc_0.number_of_days, 0, 'Cron validity passed, should not allocate any leave')

    def test_accrual_balance_limit(self):
        """ Test if accrual allocation does not allocate more than the balance limit"""
        allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'accrual 5 max',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'allocation_type': 'accrual',
            'accrual_limit': 5,
            'number_of_days': 0,
            'number_per_interval': 6,
            'interval_number': 1,
            'unit_per_interval': 'days',
            'interval_unit': 'weeks',
        })
        allocation.action_approve()
        allocation._update_accrual()

        self.assertEqual(allocation.number_of_days, 5, 'Should have allocated only 5 days as balance limit is 5')
