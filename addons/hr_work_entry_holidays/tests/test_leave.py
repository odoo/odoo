# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from freezegun import freeze_time

from odoo import SUPERUSER_ID
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

    def test_create_mark_conflicting_work_entries(self):
        work_entry = self.create_work_entry(datetime(2019, 10, 10, 9, 0), datetime(2019, 10, 10, 12, 0))
        self.assertNotEqual(work_entry.state, 'conflict', "It should not be conflicting")
        leave = self.create_leave(date(2019, 10, 10), date(2019, 10, 10))
        self.assertEqual(work_entry.state, 'conflict', "It should be conflicting")
        self.assertEqual(work_entry.leave_id, leave, "It should be linked to conflicting leave")

    def test_write_mark_conflicting_work_entries(self):
        leave = self.create_leave(date(2019, 10, 10), datetime(2019, 10, 10))
        work_entry = self.create_work_entry(leave.date_from - relativedelta(days=1), leave.date_from)  # the day before
        self.assertNotEqual(work_entry.state, 'conflict', "It should not be conflicting")
        leave.request_date_from = date(2019, 10, 9)  # now it conflicts
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
        leave = self.create_leave(date(2019, 10, 10), date(2019, 10, 10))
        work_entries = self.richard_emp.contract_id._generate_work_entries(datetime(2019, 10, 10, 0, 0, 0), datetime(2019, 10, 10, 23, 59, 59))
        adjacent_work_entry = self.create_work_entry(leave.date_from - relativedelta(days=3), leave.date_from)
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
        leave_work_entry = self.richard_emp.contract_ids.generate_work_entries(start.date(), end.date())
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

    def test_work_entry_cancel_leave(self):
        user = self.env['res.users'].create({
            'name': 'User Employee',
            'login': 'jul',
            'password': 'julpassword',
        })
        self.richard_emp.user_id = user
        self.richard_emp.contract_ids.state = 'open'
        with freeze_time(datetime(2022, 3, 21)):
            # Tests that cancelling a leave archives the work entries.
            leave = self.env['hr.leave'].with_user(user).create({
                'name': 'Sick 1 week during christmas snif',
                'employee_id': self.richard_emp.id,
                'holiday_status_id': self.leave_type.id,
                'request_date_from': date(2022, 3, 22),
                'request_date_to': date(2022, 3, 25),
            })
            leave.with_user(SUPERUSER_ID).action_validate()
            # No work entries exist yet
            self.assertTrue(leave.can_cancel, "The leave should still be cancellable")
            # can not create in the future
            self.richard_emp.contract_ids.generate_work_entries(date(2022, 3, 21), date(2022, 3, 25))
            work_entries = self.env['hr.work.entry'].search([('employee_id', '=', self.richard_emp.id)])
            leave.invalidate_recordset(['can_cancel'])
            # Work entries exist but are not locked yet
            self.assertTrue(leave.can_cancel, "The leave should still be cancellable")
            work_entries.action_validate()
            leave.invalidate_recordset(['can_cancel'])
            # Work entries locked
            self.assertFalse(leave.can_cancel, "The leave should not be cancellable")

    def test_work_entry_generation_company_time_off(self):
        existing_leaves = self.env['hr.leave'].search([])
        existing_leaves.action_refuse()
        existing_leaves.action_reset_confirm()
        existing_leaves.unlink()
        start = date(2022, 8, 1)
        end = date(2022, 8, 31)
        self.contract_cdi.generate_work_entries(start, end)
        work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.jules_emp.id),
            ('date_start', '>=', start),
            ('date_stop', '<=', end),
        ])
        self.assertEqual(len(work_entries.work_entry_type_id), 1)
        leave = self.env['hr.leave.generate.multi.wizard'].create({
            'name': 'Holiday!!!',
            'allocation_mode': 'company',
            'company_id': self.env.company.id,
            'holiday_status_id': self.leave_type.id,
            'date_from': datetime(2022, 8, 8),
            'date_to': datetime(2022, 8, 8),
        })
        leave.action_generate_time_off()
        work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.jules_emp.id),
            ('date_start', '>=', start),
            ('date_stop', '<=', end),
        ])
        self.assertEqual(len(work_entries.work_entry_type_id), 2)

    def test_time_off_duration_contract_state_change(self):
        # check that setting a contract without end state from
        # expired to running won't erase the time off duration

        leave = self.create_leave(datetime(2019, 10, 10, 9, 0), datetime(2019, 10, 10, 18, 0))
        self.assertTrue(leave.number_of_days, 1)
        contract = self.richard_emp.contract_ids
        contract.state = "close"
        contract.date_end = False
        self.assertTrue(leave.number_of_days, 1)
        contract.state = "open"
        self.assertTrue(leave.number_of_days, 1)

    def test_split_leaves_by_entry_type(self):
        entry_type_paid, entry_type_unpaid = self.env['hr.work.entry.type'].create([
            {'name': 'Paid leave', 'code': 'PAID', 'is_leave': True},
            {'name': 'Unpaid leave', 'code': 'UNPAID', 'is_leave': True},
        ])

        leave_type_paid, leave_type_unpaid = self.env['hr.leave.type'].create([{
            'name': 'Paid leave type',
            'requires_allocation': 'no',
            'request_unit': 'hour',
            'work_entry_type_id': entry_type_paid.id,
        },
        {
            'name': 'Unpaid leave type',
            'requires_allocation': 'no',
            'request_unit': 'hour',
            'work_entry_type_id': entry_type_unpaid.id,
        }])

        leave_paid, leave_unpaid = self.env['hr.leave'].create([{
            'name': 'Paid leave',
            'employee_id': self.jules_emp.id,
            'holiday_status_id': leave_type_paid.id,
            'request_date_from': datetime(2024, 9, 10),
            'request_date_to': datetime(2024, 9, 10),
            'request_unit_hours': True,
            'request_hour_from': '8',
            'request_hour_to': '9',
        },
        {
            'name': 'Unpaid leave',
            'employee_id': self.jules_emp.id,
            'holiday_status_id': leave_type_unpaid.id,
            'request_date_from': datetime(2024, 9, 10),
            'request_date_to': datetime(2024, 9, 10),
            'request_unit_hours': True,
            'request_hour_from': '9',
            'request_hour_to': '10',
        }])

        (leave_paid | leave_unpaid).with_user(SUPERUSER_ID).action_validate()
        entries = self.contract_cdi._generate_work_entries(datetime(2024, 9, 10, 0, 0, 0), datetime(2024, 9, 10, 23, 59, 59))
        paid_leave_entry = entries.filtered_domain([('work_entry_type_id', '=', entry_type_paid.id)])
        unpaid_leave_entry = entries.filtered_domain([('work_entry_type_id', '=', entry_type_unpaid.id)])

        self.assertEqual(len(entries), 4, 'Leaves should have 1 entry per type')
        self.assertEqual((paid_leave_entry.date_stop - paid_leave_entry.date_start).seconds, 3600)
        self.assertEqual((unpaid_leave_entry.date_stop - unpaid_leave_entry.date_start).seconds, 3600)

    def test_create_work_entry_for_flexible_employee_leave(self):
        entry_type_paid = self.env['hr.work.entry.type'].create([
            {'name': 'Paid leave', 'code': 'PAID', 'is_leave': True},
        ])

        leave_type_paid = self.env['hr.leave.type'].create({
            'name': 'Paid leave type',
            'requires_allocation': 'no',
            'request_unit': 'hour',
            'work_entry_type_id': entry_type_paid.id,
        })

        flex_40h_calendar = self.env['resource.calendar'].create({
            'name': 'Flexible 40h/week',
            'hours_per_day': 8.0,
            'flexible_hours': True,
        })

        self.jules_emp.resource_calendar_id = flex_40h_calendar
        self.jules_emp.contract_id.resource_calendar_id = flex_40h_calendar

        leave_paid = self.env['hr.leave'].create({
            'name': 'Paid leave',
            'employee_id': self.jules_emp.id,
            'holiday_status_id': leave_type_paid.id,
            'request_date_from': datetime(2024, 9, 10),
            'request_date_to': datetime(2024, 9, 13),
        })
        leave_paid.with_user(SUPERUSER_ID).action_validate()

        entries = self.jules_emp.contract_id.generate_work_entries(date(2024, 9, 9), date(2024, 9, 14))
        paid_leave_entry = entries.filtered_domain([('work_entry_type_id', '=', entry_type_paid.id)])

        self.assertEqual(paid_leave_entry.duration, 32, "The duration of the work entry for flexible employee should "
                                                        "be number of days * hours per day")
