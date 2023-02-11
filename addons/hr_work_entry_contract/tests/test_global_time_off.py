# # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestWorkEntryBase

from datetime import datetime

from odoo.tests import tagged

@tagged('-at_install', 'post_install')
class TestGlobalTimeOff(TestWorkEntryBase):

    def test_gto_other_calendar(self):
        # Tests that a global time off in another calendar does not affect work entry generation
        #  for other calendars
        other_calendar = self.env['resource.calendar'].create({
            'name': 'other calendar',
        })
        start = datetime(2018, 1, 1, 0, 0, 0)
        end = datetime(2018, 1, 1, 23, 59, 59)
        leave = self.env['resource.calendar.leaves'].create({
            'date_from': start,
            'date_to': end,
            'calendar_id': other_calendar.id,
            'work_entry_type_id': self.work_entry_type_leave.id,
        })
        contract = self.richard_emp.contract_ids
        contract.state = 'open'
        contract.date_generated_from = start
        contract.date_generated_to = start
        work_entries = contract._generate_work_entries(start, end)
        self.assertEqual(work_entries.work_entry_type_id, contract._get_default_work_entry_type())
        work_entries.unlink()
        contract.date_generated_from = start
        contract.date_generated_to = start
        leave.calendar_id = contract.resource_calendar_id
        work_entries = contract._generate_work_entries(start, end)
        self.assertEqual(work_entries.work_entry_type_id, leave.work_entry_type_id)
