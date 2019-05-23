# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, time, timedelta
from dateutil.relativedelta import relativedelta

from odoo import fields

from odoo.tools import mute_logger

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysBase


class TestAccrualAllocations(TestHrHolidaysBase):
    def setUp(self):
        super(TestAccrualAllocations, self).setUp()

        # Make sure we have the rights to create, validate and delete the leaves, leave types and allocations
        LeaveType = self.env['hr.leave.type'].sudo(self.user_hrmanager_id).with_context(tracking_disable=True)

        self.wk_attendance = self.ref('hr_payroll.work_entry_type_attendance')
        self.wk_unpaid = self.ref('hr_payroll.work_entry_type_unpaid_leave')

        self.accrual_type = LeaveType.create({
            'name': 'accrual',
            'allocation_type': 'fixed',
        })

        self.unpaid_type = LeaveType.create({
            'name': 'unpaid',
            'allocation_type': 'no',
            'unpaid': True,
        })

        self.set_employee_create_date(self.employee_emp_id, '2010-02-03 00:00:00')
        self.set_employee_create_date(self.employee_hruser_id, '2010-02-03 00:00:00')

        self.env['hr.contract'].create({
            'name': 'employee contract',
            'employee_id': self.employee_emp_id,
            'date_start': '2010-02-03',
            'wage': 1
        }).write({'state': 'open'})

        self.env['hr.contract'].create({
            'name': 'hr manager contract',
            'employee_id': self.employee_hruser_id,
            'date_start': '2010-02-03',
            'wage': 1
        }).write({'state': 'open'})

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

    def create_work_entry(self, employee, type_id, start, end):
        work_entry = self.env['hr.work.entry'].create({
            'name': '1',
            'employee_id': employee.id,
            'contract_id': employee.contract_id.id,
            'work_entry_type_id': type_id,
            'date_start': start,
            'date_stop': end,
        })
        work_entry.action_validate()
        work_entry._split_by_day()

    def test_accrual_base_no_leaves(self):
        """ Test if we can allocate some leaves accrually to an employee """
        alloc = self.env['hr.leave.allocation'].sudo(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'Accrual allocation for employee',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'date_from': '2010-02-03',
            'accrual': True,
            'number_of_days': 0,
            'number_per_interval': 1,
            'interval_number': 1,
            'unit_per_interval': 'days',
            'interval_unit': 'weeks',
        })
        alloc.action_approve()
        self.create_work_entry(self.employee_emp, self.wk_attendance, fields.Datetime.from_string('2019-01-01 00:00:00'), fields.Datetime.today())
        alloc.sudo()._update_accrual()

        self.assertEqual(alloc.number_of_days, 1, 'Employee should have been allocated one leave day')

    def test_accrual_base_leaves(self):
        """ Test if the accrual allocation take the unpaid leaves into account when allocating leaves """
        alloc = self.env['hr.leave.allocation'].sudo(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'Accrual allocation for employee with leaves',
            'employee_id': self.employee_hruser_id,
            'holiday_status_id': self.accrual_type.id,
            'date_from': '2010-02-03',
            'accrual': True,
            'number_of_days': 0,
            'number_per_interval': 1,
            'interval_number': 1,
            'unit_per_interval': 'days',
            'interval_unit': 'weeks',
        })

        alloc.action_approve()

        employee = self.env['hr.employee'].browse(self.employee_hruser_id)
        # Getting the previous work date
        df = employee.resource_calendar_id.plan_days(-3, fields.Datetime.now().replace(day=1)).date()

        self.create_work_entry(self.employee_hruser, self.wk_attendance, fields.Datetime.from_string('2019-01-01 00:00:00'), fields.Datetime.today())

        # update the 2nd to last work entry, with type: unpaid leave
        self.env['hr.work.entry'].search([('date_start', '=', df)]).update({'work_entry_type_id': self.wk_unpaid})

        alloc.sudo()._update_accrual()

        self.assertEqual(alloc.number_of_days, .8, 'As employee took some unpaid leaves last week, he should be allocated only .8 days')

    def test_accrual_many(self):
        """
            Test different configuration of accrual allocations
        """
        Allocation = self.env['hr.leave.allocation'].sudo(self.user_hrmanager_id).with_context(tracking_disable=True)

        alloc_0 = Allocation.create({
            'name': '1 day per 2 weeks',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'date_from': '2010-02-03',
            'accrual': True,
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
            'date_from': '2010-02-03',
            'accrual': True,
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
            'date_from': '2010-02-03',
            'accrual': True,
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
            'date_from': '2010-02-03',
            'accrual': True,
            'number_of_days': 0,
            'number_per_interval': 20,
            'interval_number': 1,
            'unit_per_interval': 'days',
            'interval_unit': 'years',
        })

        (alloc_0 | alloc_1 | alloc_2 | alloc_3).action_approve()

        self.create_work_entry(self.employee_emp, self.wk_attendance, fields.Datetime.from_string('2019-01-01 00:00:00'), fields.Datetime.today())

        Allocation.sudo()._update_accrual()

        self.assertEqual(alloc_0.number_of_days, 1)
        self.assertEqual(alloc_1.number_of_days, .5)
        self.assertEqual(alloc_2.number_of_days, 2)
        self.assertEqual(alloc_3.number_of_days, 20)

    def test_accrual_new_employee(self):
        """
            Test if accrual allocation takes into account the creation date
            of an employee
        """
        Allocation = self.env['hr.leave.allocation'].sudo(self.user_hrmanager_id).with_context(tracking_disable=True)

        self.set_employee_create_date(self.employee_emp_id, fields.Datetime.to_string(fields.Datetime.now()))

        alloc_0 = Allocation.create({
            'name': 'one shot one kill',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'accrual': True,
            'number_of_days': 0,
            'number_per_interval': 1,
            'interval_number': 1,
            'unit_per_interval': 'days',
            'interval_unit': 'weeks',
        })

        alloc_0.action_approve()

        Allocation.sudo()._update_accrual()

        self.assertEqual(alloc_0.number_of_days, 0, 'Employee is new he should not get any accrual leaves')

    def test_accrual_multi(self):
        """ Test if the cron does not allocate leaves every time it's called but only when necessary """
        alloc = self.env['hr.leave.allocation'].sudo(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': '2 days per week',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'date_from': '2010-02-03',
            'accrual': True,
            'number_of_days': 0,
            'number_per_interval': 1,
            'interval_number': 2,
            'unit_per_interval': 'days',
            'interval_unit': 'weeks',
        })
        alloc.action_approve()
        self.create_work_entry(self.employee_emp, self.wk_attendance, fields.Datetime.from_string('2019-01-01 00:00:00'), fields.Datetime.today())
        alloc.sudo()._update_accrual()
        alloc.sudo()._update_accrual()

        self.assertEqual(alloc.number_of_days, 1, 'Cron only allocates 1 days every two weeks')

    def test_accrual_validation(self):
        """
            Test if cron does not allocate past it's validity date
        """
        Allocation = self.env['hr.leave.allocation'].sudo(self.user_hrmanager_id).with_context(tracking_disable=True)

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

        Allocation.sudo()._update_accrual()

        self.assertEqual(alloc_0.number_of_days, 0, 'Cron validity passed, should not allocate any leave')

    def test_accrual_balance_limit(self):
        """ Test if accrual allocation does not allocate more than the balance limit"""
        allocation = self.env['hr.leave.allocation'].sudo(self.user_hrmanager_id).with_context(tracking_disable=True).create({
            'name': 'accrual 5 max',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'date_from': '2010-02-03',
            'accrual': True,
            'accrual_limit': 5,
            'number_of_days': 0,
            'number_per_interval': 6,
            'interval_number': 1,
            'unit_per_interval': 'days',
            'interval_unit': 'weeks',
        })
        allocation.action_approve()

        self.create_work_entry(self.employee_emp, self.wk_attendance, fields.Datetime.from_string('2019-01-01 00:00:00'), fields.Datetime.today())
        allocation.sudo()._update_accrual()
        self.assertEqual(allocation.number_of_days, 5, 'Should have allocated only 5 days as balance limit is 5')
