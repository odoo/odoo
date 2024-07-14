# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo.tests.common import TransactionCase

class TestCommon(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.user.tz = 'Europe/Brussels'

        self.calendar = self.env['resource.calendar'].create({
            'name': 'Calendar',
        })
        self.env.company.resource_calendar_id = self.calendar

        # Employees
        self.patrick = self.env['hr.employee'].create({
            'name': 'patrick',
            'tz': 'UTC',
            'resource_calendar_id': self.calendar.id,
        })
        self.res_patrick = self.patrick.resource_id
        self.bob = self.env['hr.employee'].create({
            'name': 'bob',
            'tz': 'UTC',
        })
        self.res_bob = self.bob.resource_id

        # Leave type
        self.leave_type = self.env['hr.leave.type'].create({
            'name': 'time off',
            'requires_allocation': 'no',
            'request_unit': 'hour',
        })

        # Allocations
        self.allocation_patrick = self.env['hr.leave.allocation'].create({
            'state': 'confirm',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.patrick.id,
            'date_from': time.strftime('%Y-01-01'),
            'date_to': time.strftime('%Y-12-31'),
        })
        self.allocation_bob = self.env['hr.leave.allocation'].create({
            'state': 'confirm',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.bob.id,
            'date_from': time.strftime('%Y-01-01'),
            'date_to': time.strftime('%Y-12-31'),
        })
        (self.allocation_patrick | self.allocation_bob).action_validate()
