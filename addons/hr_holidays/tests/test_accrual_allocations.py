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

