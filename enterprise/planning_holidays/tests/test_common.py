# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo.addons.planning.tests.common import TestCommonPlanning

class TestCommon(TestCommonPlanning):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.setUpEmployees()
        cls.setUpDates()

        cls.env.user.tz = 'Europe/Brussels'
        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Calendar',
        })
        cls.env.company.resource_calendar_id = cls.calendar

        # Leave type
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'time off',
            'requires_allocation': 'no',
            'request_unit': 'hour',
        })

        # Allocations
        cls.allocation_bert = cls.env['hr.leave.allocation'].create({
            'state': 'confirm',
            'holiday_status_id': cls.leave_type.id,
            'employee_id': cls.employee_bert.id,
            'date_from': time.strftime('%Y-01-01'),
            'date_to': time.strftime('%Y-12-31'),
        })
        cls.allocation_bert.action_validate()
