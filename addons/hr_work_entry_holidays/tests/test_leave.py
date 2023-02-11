# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo.addons.hr_work_entry_holidays.tests.common import TestWorkEntryHolidaysBase
from odoo.tests import tagged

@tagged('test_leave')
class TestWorkEntryLeave(TestWorkEntryHolidaysBase):

    def test_resource_leave_has_work_entry_type(self):
        leave = self.create_leave()

        resource_leave = leave._create_resource_leave()
        self.assertEqual(resource_leave.work_entry_type_id, self.leave_type.work_entry_type_id, "it should have the corresponding work_entry type")

    def test_resource_leave_in_contract_calendar(self):
        other_calendar = self.env['resource.calendar'].create({'name': 'New calendar'})
        contract = self.richard_emp.contract_ids[0]
        contract.resource_calendar_id = other_calendar
        contract.state = 'open'  # this set richard's calendar to New calendar
        leave = self.create_leave()

        resource_leave = leave._create_resource_leave()
        self.assertEqual(len(resource_leave), 1, "it should have created only one resource leave")
        self.assertEqual(resource_leave.work_entry_type_id, self.leave_type.work_entry_type_id, "it should have the corresponding work_entry type")

    def test_resource_leave_different_calendars(self):
        other_calendar = self.env['resource.calendar'].create({'name': 'New calendar'})
        contract = self.richard_emp.contract_ids[0]
        contract.resource_calendar_id = other_calendar
        contract.state = 'open'  # this set richard's calendar to New calendar

        # set another calendar
        self.richard_emp.resource_calendar_id = self.env['resource.calendar'].create({'name': 'Other calendar'})

        leave = self.create_leave()
        resource_leave = leave._create_resource_leave()
        self.assertEqual(len(resource_leave), 2, "it should have created one resource leave per calendar")
        self.assertEqual(resource_leave.mapped('work_entry_type_id'), self.leave_type.work_entry_type_id, "they should have the corresponding work_entry type")

    def test_create_mark_conflicting_work_entries(self):
        work_entry = self.create_work_entry(datetime(2019, 10, 10, 9, 0), datetime(2019, 10, 10, 12, 0))
        self.assertNotEqual(work_entry.state, 'conflict', "It should not be conflicting")
        leave = self.create_leave(datetime(2019, 10, 10, 9, 0), datetime(2019, 10, 10, 18, 0))
        self.assertEqual(work_entry.state, 'conflict', "It should be conflicting")
        self.assertEqual(work_entry.leave_id, leave, "It should be linked to conflicting leave")

    def test_write_mark_conflicting_work_entries(self):
        leave = self.create_leave(datetime(2019, 10, 10, 9, 0), datetime(2019, 10, 10, 12, 0))
        work_entry = self.create_work_entry(datetime(2019, 10, 9, 9, 0), datetime(2019, 10, 10, 9, 0))  # the day before
        self.assertNotEqual(work_entry.state, 'conflict', "It should not be conflicting")
        leave.date_from = datetime(2019, 10, 9, 9, 0)  # now it conflicts
        self.assertEqual(work_entry.state, 'conflict', "It should be conflicting")
        self.assertEqual(work_entry.leave_id, leave, "It should be linked to conflicting leave")

    def test_validate_leave_with_overlap(self):
        contract = self.richard_emp.contract_ids[:1]
        contract.state = 'open'
        contract.date_generated_from = datetime(2019, 10, 10, 9, 0)
        contract.date_generated_to = datetime(2019, 10, 10, 9, 0)
        leave = self.create_leave(datetime(2019, 10, 10, 9, 0), datetime(2019, 10, 12, 18, 0))
        work_entry_1 = self.create_work_entry(datetime(2019, 10, 8, 9, 0), datetime(2019, 10, 11, 9, 0))  # overlaps
        work_entry_2 = self.create_work_entry(datetime(2019, 10, 11, 9, 0), datetime(2019, 10, 11, 10, 0))  # included
        adjacent_work_entry = self.create_work_entry(datetime(2019, 10, 12, 18, 0), datetime(2019, 10, 13, 18, 0))  # after and don't overlap
        leave.action_validate()
        self.assertNotEqual(adjacent_work_entry.state, 'conflict', "It should not conflict")
        self.assertFalse(work_entry_2.active, "It should have been archived")
        self.assertEqual(work_entry_1.state, 'conflict', "It should conflict")
        self.assertFalse(work_entry_1.leave_id, "It should not be linked to the leave")

        leave_work_entry = self.env['hr.work.entry'].search([('leave_id', '=', leave.id)]) - work_entry_1
        self.assertTrue(leave_work_entry.work_entry_type_id.is_leave, "It should have created a leave work entry")
        self.assertEqual(leave_work_entry[:1].state, 'conflict', "The leave work entry should conflict")

    def test_conflict_move_work_entry(self):
        leave = self.create_leave(datetime(2019, 10, 10, 9, 0), datetime(2019, 10, 12, 18, 0))
        work_entry = self.create_work_entry(datetime(2019, 10, 8, 9, 0), datetime(2019, 10, 11, 9, 0))  # overlaps
        self.assertEqual(work_entry.state, 'conflict', "It should be conflicting")
        self.assertEqual(work_entry.leave_id, leave, "It should be linked to conflicting leave")
        work_entry.date_stop = datetime(2019, 10, 9, 9, 0)  # no longer overlaps
        self.assertNotEqual(work_entry.state, 'conflict', "It should not be conflicting")
        self.assertFalse(work_entry.leave_id, "It should not be linked to any leave")

    def test_validate_leave_without_overlap(self):
        contract = self.richard_emp.contract_ids[:1]
        contract.state = 'open'
        contract.date_generated_from = datetime(2019, 10, 10, 9, 0)
        contract.date_generated_to = datetime(2019, 10, 10, 9, 0)
        leave = self.create_leave(datetime(2019, 10, 10, 9, 0), datetime(2019, 10, 12, 18, 0))
        work_entry = self.create_work_entry(datetime(2019, 10, 11, 9, 0), datetime(2019, 10, 11, 10, 0))  # included
        leave.action_validate()
        self.assertFalse(work_entry[:1].active, "It should have been archived")

        leave_work_entry = self.env['hr.work.entry'].search([('leave_id', '=', leave.id)])
        self.assertTrue(leave_work_entry.work_entry_type_id.is_leave, "It should have created a leave work entry")
        self.assertNotEqual(leave_work_entry[:1].state, 'conflict', "The leave work entry should not conflict")

    def test_refuse_leave(self):
        leave = self.create_leave(datetime(2019, 10, 10, 9, 0), datetime(2019, 10, 10, 18, 0))
        work_entries = self.richard_emp.contract_id._generate_work_entries(datetime(2019, 10, 10, 9, 0), datetime(2019, 10, 10, 18, 0))
        adjacent_work_entry = self.create_work_entry(datetime(2019, 10, 7, 9, 0), datetime(2019, 10, 10, 9, 0))
        self.assertTrue(all(work_entries.mapped(lambda w: w.state == 'conflict')), "Attendance work entries should all conflict with the leave")
        self.assertNotEqual(adjacent_work_entry.state, 'conflict', "Non overlapping work entry should not conflict")
        leave.action_refuse()
        self.assertTrue(all(work_entries.mapped(lambda w: w.state != 'conflict')), "Attendance work entries should no longer conflict")
        self.assertNotEqual(adjacent_work_entry.state, 'conflict', "Non overlapping work entry should not conflict")

    def test_refuse_approved_leave(self):
        start = datetime(2019, 10, 10, 6, 0)
        end = datetime(2019, 10, 10, 18, 0)

        # Setup contract generation state
        contract = self.richard_emp.contract_ids[:1]
        contract.state = 'open'
        contract.date_generated_from = start - relativedelta(hours=1)
        contract.date_generated_to = start - relativedelta(hours=1)

        leave = self.create_leave(start, end)
        leave.action_validate()
        work_entries = self.env['hr.work.entry'].search([('employee_id', '=', self.richard_emp.id), ('date_start', '<=', end), ('date_stop', '>=', start)])
        leave_work_entry = self.richard_emp.contract_ids._generate_work_entries(start, end)
        self.assertEqual(leave_work_entry[:1].leave_id, leave)
        leave.action_refuse()
        work_entries = self.env['hr.work.entry'].search([('employee_id', '=', self.richard_emp.id), ('date_start', '>=', start), ('date_stop', '<=', end)])
        self.assertFalse(leave_work_entry[:1].filtered('leave_id').active)
        self.assertEqual(len(work_entries), 2, "Attendance work entries should have been re-created (morning and afternoon)")
        self.assertTrue(all(work_entries.mapped(lambda w: w.state != 'conflict')), "Attendance work entries should not conflict")

    def test_archived_work_entry_conflict(self):
        self.create_leave(datetime(2019, 10, 10, 9, 0), datetime(2019, 10, 10, 18, 0))
        work_entry = self.create_work_entry(datetime(2019, 10, 10, 9, 0), datetime(2019, 10, 10, 18, 0))
        self.assertTrue(work_entry.active)
        self.assertEqual(work_entry.state, 'conflict', "Attendance work entries should conflict with the leave")
        work_entry.toggle_active()
        self.assertEqual(work_entry.state, 'cancelled', "Attendance work entries should be cancelled and not conflict")
        self.assertFalse(work_entry.active)

    def test_work_entry_generation_company_time_off(self):
        existing_leaves = self.env['hr.leave'].search([])
        existing_leaves.action_refuse()
        existing_leaves.action_draft()
        existing_leaves.unlink()
        start = date(2022, 8, 1)
        end = date(2022, 8, 31)
        self.contract_cdi._generate_work_entries(start, end)
        work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.jules_emp.id),
            ('date_start', '>=', start),
            ('date_stop', '<=', end),
        ])
        self.assertEqual(len(work_entries.work_entry_type_id), 1)
        leave = self.env['hr.leave'].create({
            'name': 'Holiday !!!',
            'holiday_type': 'company',
            'mode_company_id': self.env.company.id,
            'holiday_status_id': self.leave_type.id,
            'date_from': datetime(2022, 8, 8, 9, 0),
            'date_to': datetime(2022, 8, 8, 18, 0),
            'number_of_days': 1,
        })
        leave.action_validate()
        work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.jules_emp.id),
            ('date_start', '>=', start),
            ('date_stop', '<=', end),
        ])
        self.assertEqual(len(work_entries.work_entry_type_id), 2)
