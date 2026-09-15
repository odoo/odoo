# # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo.tests import tagged
from odoo.addons.hr_work_entry_holidays.tests.common import TestWorkEntryHolidaysBase


@tagged('work_entry_multi_contract')
class TestWorkEntryHolidaysMultiContract(TestWorkEntryHolidaysBase):

    def test_multi_contract_holiday(self):
        # Leave during second contract
        leave = self.create_leave(datetime(2015, 11, 17), datetime(2015, 11, 20), name="Doctor Appointment", employee_id=self.jules_emp.id)
        leave.action_approve()
        start = datetime(2015, 11, 1, 0, 0, 0)
        end_generate = datetime(2015, 11, 30, 23, 59, 59)
        work_entries = self.jules_emp.contract_ids._generate_work_entries(start, end_generate)
        work_entries.action_validate()
        work_entries = work_entries.filtered(lambda we: we.contract_id == self.contract_cdi)

        work = work_entries.filtered(lambda line: line.work_entry_type_id == self.env.ref('hr_work_entry.work_entry_type_attendance'))
        leave = work_entries.filtered(lambda line: line.work_entry_type_id == self.work_entry_type_leave)
        self.assertEqual(sum(work.mapped('duration')), 49, "It should be 49 hours of work this month for this contract")
        self.assertEqual(sum(leave.mapped('duration')), 28, "It should be 28 hours of leave this month for this contract")

    def test_leave_overlaps_with_two_contracts(self):
        emp = self.env['hr.employee'].create({
            'name': 'Jules',
        })
        contract_first = self.env['hr.contract'].create({
            'date_start': datetime.strptime('2026-01-01', '%Y-%m-%d'),
            'name': 'First Contract for Emp',
            'resource_calendar_id': self.calendar_40h.id,
            'wage': 5000.0,
            'employee_id': emp.id,
            'state': 'open',
            'kanban_state': 'blocked',
        })
        contract_first._generate_work_entries(datetime(2026, 7, 1, 0, 0, 0), datetime(2026, 7, 31, 23, 59, 59))
        contract_first.write({
            'date_end': datetime.strptime('2026-07-21', '%Y-%m-%d'),
        })
        self.env['hr.contract'].create({
            'date_start': datetime.strptime('2026-07-22', '%Y-%m-%d'),
            'name': 'Second Contract for Emp',
            'resource_calendar_id': self.calendar_40h.id,
            'wage': 5000.0,
            'employee_id': emp.id,
            'state': 'open',
            'kanban_state': 'blocked',
        })

        leave = self.create_leave(datetime(2026, 7, 15), datetime(2026, 7, 22), name="Doctor Appointment",
                                  employee_id=emp.id)
        leave.action_approve()

        work_entries = self.env['hr.work.entry'].search([('employee_id', '=', emp.id)])

        leave_entries = work_entries.filtered(lambda we: we.work_entry_type_id == self.work_entry_type_leave)
        self.assertEqual(sum(leave_entries.mapped('duration')), 40,
            "Only the 5 leave days covered by the first contract should be generated")
        self.assertEqual(len(leave_entries), 10,
            "Only 10 work entries should be generated 2 for each day, ignoring the last day which lays in the second contract")
