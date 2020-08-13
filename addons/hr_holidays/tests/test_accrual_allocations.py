# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, time
from dateutil.relativedelta import relativedelta

from odoo import fields

from odoo.tools import mute_logger, DEFAULT_SERVER_DATE_FORMAT

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestAccrualAllocations(TestHrHolidaysCommon):
    def setUp(self):
        super(TestAccrualAllocations, self).setUp()

        WorkEntryType = self.env['hr.work.entry.type'].with_context(tracking_disable=True)
        self.work_entry_type = WorkEntryType.create({
            'name': 'Hr Work Entry Type for Accrual Allocation',
            'code': 'ACCRUAL',
            'property_leave_right': True,
        })

        LeaveType = self.env['hr.leave.type'].with_user(self.user_hrmanager_id).with_context(tracking_disable=True)

        self.accrual_type = LeaveType.create({
            'name': 'accrual',
            'allocation_type': 'fixed',
            'validity_start': False,
            'work_entry_type_id': self.work_entry_type.id
        })

        self.unpaid_type = LeaveType.create({
            'name': 'unpaid',
            'allocation_type': 'no',
            'unpaid': True,
            'validity_start': False,
        })

        self.set_employee_create_date(self.employee_hruser_id, (datetime.today()-relativedelta(days=8)).strftime(DEFAULT_SERVER_DATE_FORMAT))

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
        alloc = self.env['hr.leave.allocation'].with_user(self.user_hrmanager_id).with_context(
            tracking_disable=True).create({
            'name': 'Accrual allocation for employee',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.accrual_type.id,
            'allocation_type': 'accrual',
        })
        alloc.action_approve()
        alloc._update_accrual()

        self.assertEqual(alloc.number_of_days, 1, 'Employee should have been allocated one leave day')

