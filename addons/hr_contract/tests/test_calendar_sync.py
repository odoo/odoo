# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Datetime, Date
from odoo.addons.hr_contract.tests.common import TestContractCommon


class TestContractCalendars(TestContractCommon):

    @classmethod
    def setUpClass(cls):
        super(TestContractCalendars, cls).setUpClass()
        cls.calendar_richard = cls.env['resource.calendar'].create({'name': 'Calendar of Richard'})
        cls.employee.resource_calendar_id = cls.calendar_richard

        cls.calendar_35h = cls.env['resource.calendar'].create({'name': '35h calendar'})
        cls.calendar_35h._onchange_hours_per_day()  # update hours/day

        cls.contract_cdd = cls.env['hr.contract'].create({
            'date_end': Date.to_date('2015-11-15'),
            'date_start': Date.to_date('2015-01-01'),
            'name': 'First CDD Contract for Richard',
            'resource_calendar_id': cls.calendar_35h.id,
            'wage': 5000.0,
            'employee_id': cls.employee.id,
            'state': 'close',
        })

    def test_contract_state_incoming_to_open(self):
        # Employee's calendar should change
        self.assertEqual(self.employee.resource_calendar_id, self.calendar_richard)
        self.contract_cdd.state = 'open'
        self.assertEqual(self.employee.resource_calendar_id, self.contract_cdd.resource_calendar_id, "The employee should have the calendar of its contract.")

    def test_contract_transfer_leaves(self):

        def create_calendar_leave(start, end, resource=None):
            return self.env['resource.calendar.leaves'].create({
                'name': 'leave name',
                'date_from': start,
                'date_to': end,
                'resource_id': resource.id if resource else None,
                'calendar_id': self.employee.resource_calendar_id.id,
                'time_type': 'leave',
            })

        start = Datetime.to_datetime('2015-11-17 07:00:00')
        end = Datetime.to_datetime('2015-11-20 18:00:00')
        leave1 = create_calendar_leave(start, end, resource=self.employee.resource_id)

        start = Datetime.to_datetime('2015-11-25 07:00:00')
        end = Datetime.to_datetime('2015-11-28 18:00:00')
        leave2 = create_calendar_leave(start, end, resource=self.employee.resource_id)

        # global leave
        start = Datetime.to_datetime('2015-11-25 07:00:00')
        end = Datetime.to_datetime('2015-11-28 18:00:00')
        leave3 = create_calendar_leave(start, end)

        self.calendar_richard.transfer_leaves_to(self.calendar_35h, resources=self.employee.resource_id, from_date=Date.to_date('2015-11-21'))

        self.assertEqual(leave1.calendar_id, self.calendar_richard, "It should stay in Richard's calendar")
        self.assertEqual(leave3.calendar_id, self.calendar_richard, "Global leave should stay in original calendar")
        self.assertEqual(leave2.calendar_id, self.calendar_35h, "It should be transfered to the other calendar")

        # Transfer global leaves
        self.calendar_richard.transfer_leaves_to(self.calendar_35h, resources=None, from_date=Date.to_date('2015-11-21'))

        self.assertEqual(leave3.calendar_id, self.calendar_35h, "Global leave should be transfered")