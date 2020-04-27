# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from freezegun import freeze_time
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import tagged
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged('post_install')
class TestAccrualAllocations(TestHrHolidaysCommon):
    def setUp(self):
        super(TestAccrualAllocations, self).setUp()

        WorkEntryType = self.env['hr.work.entry.type'].with_context(tracking_disable=True)
        self.work_entry_type = WorkEntryType.create({
            'name': 'Hr Work Entry Type for Accrual Allocation',
            'code': 'ACCRUAL',
            'leave_right': True,
        })

        LeaveType = self.env['hr.leave.type'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True)
        self.accrual_type = LeaveType.create({
            'name': 'accrual',
            'allocation_type': 'fixed',
            'validity_start': False,
        })

        self.accrual_user = self.env['hr.employee'].create({
            'name': 'Accrual user',
            'start_work_date': datetime.today() - relativedelta(years=3),
        })

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
        """ Test if we can allocate some leaves accrual to an employee """
        alloc = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'Accrual allocation for employee',
            'accrual_plan_id': self.accrual_plan.id,
            'employee_id': self.accrual_user.id,
            'holiday_status_id': self.accrual_type.id,
            'allocation_type': 'accrual',
        })
        alloc.action_approve()
        alloc.nextcall = False
        # we force the update now, else, it will occurs the next tuesday
        alloc.linked_request_ids.nextcall = False
        alloc._update_accrual()

        self.assertEqual(alloc.number_of_days, 0, 'Allocation should have no leave day')
        self.assertEqual(alloc.linked_request_ids.number_of_days, 1.0, 'Item should have been allocated 1 leave day')
        self.assertEqual(alloc.linked_request_ids.number_of_hours, 8.0, 'Item should have been allocated 1 leave hour')
        self.assertEqual(self.accrual_user.leaves_count, 1.0, 'Employee should have 1 day')
        # Allocation for only one employee can see their allocation plan overriden
        alloc.write({'accrual_plan_id': self.accrual_plan_monthly.id, 'nextcall': False})
        alloc.linked_request_ids.nextcall = False
        alloc._update_accrual()
        self.assertEqual(alloc.linked_request_ids.number_of_days, 2, 'Item should have been allocated 2 leave day')
        self.assertEqual(alloc.linked_request_ids.number_of_hours, 16.0, 'Item should have been allocated 9 leave hour')
        # Calculate the actual leaves of the employee after invalidating the cache to force the sql request
        self.accrual_user.invalidate_cache()
        leaves_count = round(self.accrual_user.leaves_count, 2)
        self.assertEqual(leaves_count, 2.0, 'Employee should have 2 days')

    def test_modification_on_employee(self):
        """
            When the department, category_ids or company of an employee is modified, the accrual allocations
            are recalculated according to the employee properties
        """

        AccrualPlan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True)
        plan1 = AccrualPlan.create({
            'name': 'Accrual Plan For Test',
            'accrual_ids': [(0, 0, {
                'name': '1 day per 2 weeks',
                'start_count': 0,
                'start_type': 'day',
                'added_days': 1,
                'frequency': 'bimonthly',
                'maximum_leave': 1000
            })],
        })
        plan2 = AccrualPlan.create({
            'name': 'Accrual Plan For Test',
            'accrual_ids': [(0, 0, {
                'name': '1 day per 2 weeks',
                'start_count': 0,
                'start_type': 'day',
                'added_days': 1,
                'frequency': 'bimonthly',
                'maximum_leave': 1000
            })],
        })
        department = self.env['hr.department'].with_context(tracking_disable=True).create({
            'name': 'Accrual Dept',
        })
        tag = self.env['hr.employee.category'].with_context(tracking_disable=True).create({'name': 'Tag test'})
        employee = self.env['hr.employee'].create({
            'name': 'Emp 0',
            'start_work_date': datetime.today() - relativedelta(years=3)
        })
        Allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True)
        alloc_dep = Allocation.create({
            'name': 'Allocation many',
            'holiday_status_id': self.accrual_type.id,
            'allocation_type': 'accrual',
            'accrual_plan_id': plan1.id,
            'holiday_type': 'department',
            'department_id': department.id,
        })

        alloc_tag = Allocation.create({
            'name': 'Allocation many',
            'holiday_status_id': self.accrual_type.id,
            'allocation_type': 'accrual',
            'accrual_plan_id': plan2.id,
            'holiday_type': 'category',
            'category_id': tag.id,
        })
        alloc_dep.action_approve()
        alloc_tag.action_approve()
        employee_items_ids = (alloc_dep | alloc_tag).mapped('linked_request_ids')

        # Employee should not have any accrual because he is not in the right categories
        self.assertEqual(employee_items_ids.ids, [], 'Employee is not in the right deparment, has no tag and no items are created')
        employee.write({'category_ids': [(6, None, tag.ids)], 'department_id': department.id})
        # Writing on employee trigger the plan_id calculation on the item and set nextcall
        alloc_dep.linked_request_ids.nextcall = False
        alloc_tag.linked_request_ids.nextcall = False
        Allocation._update_accrual()
        # Calculate the actual leaves of the employee after invalidating the cache to force the sql request
        employee.invalidate_cache()
        self.assertEqual(employee.leaves_count, 2.0, 'Employee should have 2 days available accrual for his tag and department')
        # Remove the tag and department on the employee, he should not accrue anymore but he keeps the holidays he accrued
        employee.write({'category_ids': [(5, 0, 0)], 'department_id': False})

        alloc_dep.nextcall = False
        alloc_dep.linked_request_ids.nextcall = False
        alloc_tag.nextcall = False
        alloc_tag.linked_request_ids.nextcall = False
        Allocation._update_accrual()
        employee.invalidate_cache()
        self.assertEqual(employee.leaves_count, 2.0, 'Employee should have kept his 2 days without accrue')




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
        })

        alloc_0.action_approve()

        Allocation._update_accrual()

        self.assertEqual(alloc_0.number_of_days, 0, 'Employee is new he should not get any accrual leaves')

    def test_accrual_multi(self):
        """ Test if the cron does not allocate leaves every time it's called but only when necessary """
        alloc = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'Cron multi',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.accrual_type.id,
            'allocation_type': 'accrual',
            'accrual_plan_id': self.accrual_plan.id,
        })
        alloc.action_approve()
        alloc.write({'nextcall': False})
        # We write some available leaves
        alloc.linked_request_ids.write({'nextcall': False})
        alloc._update_accrual()
        alloc._update_accrual()
        self.assertEqual(self.employee_emp.leaves_count, 1.0, 'Cron only allocates 1 day every week')

    def test_accrual_validation(self):
        """ Test if cron does not allocate past it's validity date """
        Allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True)

        alloc = Allocation.create({
            'name': '20 days per year',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.accrual_type.id,
            'allocation_type': 'accrual',
            'date_to': fields.Datetime.from_string('2015-02-03 00:00:00'),
            'accrual_plan_id': self.accrual_plan.id,
        })
        alloc.action_approve()
        Allocation._update_accrual()
        self.assertEqual(self.employee_emp.leaves_count, 0, 'Cron validity passed, should not allocate any leave')

    def test_accrual_balance_limit(self):
        """ Test if accrual allocation does not allocate more than the balance limit"""
        AccrualPlan = self.env['hr.leave.accrual.plan'].with_context(tracking_disable=True)
        plan = AccrualPlan.create({
            'name': 'Accrual Plan with max',
            'accrual_ids': [(0, 0, {
                'name': '2 day weekly but maxed at 5',
                'start_count': 0,
                'start_type': 'day',
                'added_days': 2,
                'frequency': 'weekly',
                'maximum_leave': 5 # 5 days max
            })],
        })
        # self.accrual_user.write({'accrual_plan_ids': [(6, 0, [plan.id])]})
        allocation = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'accrual 5 max',
            'employee_id': self.accrual_user.id,
            'holiday_status_id': self.accrual_type.id,
            'allocation_type': 'accrual',
            'accrual_plan_id': plan.id
        })
        allocation.action_approve()
        # We write some available leaves close to the limit
        allocation.linked_request_ids.write({'number_of_days': 4, 'number_of_hours': 32, 'nextcall': False})
        allocation._update_accrual()

        self.assertEqual(self.accrual_user.leaves_count, 5, 'Should have allocated only 5 days as balance limit is 5')

    @freeze_time("2020-01-19 14:00:00")
    def test_accrual_leaves_unpaid(self):
        """ Test if the unpaid leaves don't accrue and the amount of accrued hours is lower than what is given when
            no unpaid leave is taken
        """
        unpaid_leave = self.env['hr.leave.type'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'unpaid',
            'allocation_type': 'no',
            'unpaid': True,
            'validity_start': False,
        })
        alloc = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'Accrual allocation for employee with leaves',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.accrual_type.id,
            'allocation_type': 'accrual',
            'accrual_plan_id': self.accrual_plan_monthly.id
        })
        alloc.action_approve()
        alloc.write({'nextcall': False})
        leave_unpaid = self.env['hr.leave'].create({
            'name': 'leave',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': unpaid_leave.id,
            'date_from': datetime.today().replace(hour=0, minute=0, second=0) - relativedelta(days=7),
            'date_to': datetime.today().replace(hour=0, minute=0, second=0) - relativedelta(days=5),
            'number_of_days': 2,
        })
        leave_unpaid.action_validate()
        alloc.linked_request_ids.nextcall = False
        alloc._update_accrual()
        leave_days = round(alloc.linked_request_ids.number_of_days, 2)
        leave_hours = round(alloc.linked_request_ids.number_of_hours, 2)
        # As the calculation depend on the period, we can only be sure that leaves are taken into account and
        # the prorata is < in _compute_accrual_hours in the _update_accural_items method

        self.assertTrue(leave_days < 1, "Employee should have accrued less than a day")
        self.assertTrue(leave_hours < 8, "Employee should have accrued less than 8 hours")

    @freeze_time("2020-01-19 14:00:00")
    def test_accrual_leaves_leave_right(self):
        """ Test if the leaves type with property leave_right: false
            don't accrue and the amount of accrued hours is lower than what is given when no leave is taken
                """
        alloc = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'Accrual allocation for employee with leaves',
            'employee_id': self.accrual_user.id,
            'holiday_status_id': self.accrual_type.id,
            'allocation_type': 'accrual',
            'accrual_plan_id': self.accrual_plan_monthly.id
        })
        work_entry_type = self.env['hr.work.entry.type'].with_context(tracking_disable=True).create({
            'name': 'Unpaid type work entry',
            'code': 'UNPAID',
            'leave_right': False
        })
        sick_type = self.env['hr.leave.type'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'sick leave',
            'allocation_type': 'no',
            'validity_start': False,
        })
        alloc.action_approve()
        alloc.write({'nextcall': False})
        # left work for 4 days to avoid weekends
        start_unpaid_sick = datetime.today().replace(hour=0, minute=0, second=0) - relativedelta(days=7)
        stop_unpaid_sick = datetime.today().replace(hour=0, minute=0, second=0) - relativedelta(days=5)
        leave_sick_without_right = self.env['hr.leave'].create({
            'name': 'sick leave',
            'employee_id': self.accrual_user.id,
            'holiday_status_id': sick_type.id,
            'date_from': start_unpaid_sick,
            'date_to': stop_unpaid_sick,
            'number_of_days': 3,
        })
        leave_sick_without_right.action_validate()
        # We force the leave type for the leave as work_entry_holiday is not installed
        leave_ids = self.accrual_user.resource_calendar_id.leave_ids.filtered(
            lambda l: l.date_from >= start_unpaid_sick and
                      l.date_to <= stop_unpaid_sick)
        leave_ids.write({'work_entry_type_id': work_entry_type.id})

        alloc.linked_request_ids.nextcall = False
        alloc._update_accrual()
        self.assertTrue(alloc.linked_request_ids.number_of_days < 1, "Employee should have accrued than a day")
        self.assertTrue(alloc.linked_request_ids.number_of_hours < 8, "Employee should have accrued less than 8 hours")
