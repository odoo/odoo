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
        contract = self.richard_emp.version_id
        contract.resource_calendar_id = other_calendar
        leave = self.create_leave()

        resource_leave = leave._create_resource_leave()
        self.assertEqual(len(resource_leave), 1, "it should have created only one resource leave")
        self.assertEqual(resource_leave.work_entry_type_id, self.leave_type.work_entry_type_id, "it should have the corresponding work_entry type")

    def test_validate_leave_without_overlap(self):
        contract = self.richard_emp.version_id
        contract.date_generated_from = datetime(2019, 10, 10, 9, 0)
        contract.date_generated_to = datetime(2019, 10, 10, 9, 0)
        leave = self.create_leave(datetime(2019, 10, 10, 9, 0), datetime(2019, 10, 12, 18, 0))
        work_entry = self.create_work_entry(datetime(2019, 10, 11, 9, 0), datetime(2019, 10, 11, 10, 0))  # included
        leave.action_approve()
        self.assertFalse(work_entry[:1].active, "It should have been archived")

        leave_work_entry = self.env['hr.work.entry'].search([('leave_id', '=', leave.id)])
        self.assertTrue(leave_work_entry.work_entry_type_id.is_leave, "It should have created a leave work entry")
        self.assertNotEqual(leave_work_entry[:1].state, 'conflict', "The leave work entry should not conflict")

    def test_refuse_approved_leave(self):
        start = datetime(2019, 10, 10, 6, 0)
        end = datetime(2019, 10, 10, 18, 0)
        # Setup contract generation state
        contract = self.richard_emp.version_id
        contract.date_generated_from = start - relativedelta(hours=1)
        contract.date_generated_to = start - relativedelta(hours=1)

        leave = self.create_leave(start, end)
        leave.action_approve()
        work_entries = self.env['hr.work.entry'].search([('employee_id', '=', self.richard_emp.id), ('date', '<=', end), ('date', '>=', start)])
        leave_work_entry = self.richard_emp.version_id.generate_work_entries(start.date(), end.date())
        self.assertEqual(leave_work_entry[:1].leave_id, leave)
        leave.action_refuse()
        work_entries = self.env['hr.work.entry'].search([('employee_id', '=', self.richard_emp.id), ('date', '>=', start), ('date', '<=', end)])
        self.assertFalse(leave_work_entry[:1].filtered('leave_id').active)
        self.assertEqual(len(work_entries), 1, "Attendance work entry should have been re-created")
        self.assertTrue(all(work_entries.mapped(lambda w: w.state != 'conflict')), "Attendance work entries should not conflict")

    def test_work_entry_create_leave(self):
        self.create_leave(datetime(2019, 10, 10, 9, 0), datetime(2019, 10, 10, 18, 0))
        work_entry = self.create_work_entry(datetime(2019, 10, 10, 9, 0), datetime(2019, 10, 10, 18, 0))
        self.assertTrue(work_entry.active)
        self.assertEqual(work_entry.state, 'draft', "Attendance work entries don't conflict with leave requests which are in draft state.")

    def test_work_entry_cancel_leave(self):
        user = self.env['res.users'].create({
            'name': 'User Employee',
            'login': 'jul',
            'password': 'julpassword',
        })
        self.richard_emp.user_id = user
        with freeze_time(datetime(2022, 3, 21)):
            # Tests that cancelling a leave archives the work entries.
            leave = self.env['hr.leave'].with_user(user).create({
                'name': 'Sick 1 week during christmas snif',
                'employee_id': self.richard_emp.id,
                'holiday_status_id': self.leave_type.id,
                'request_date_from': date(2022, 3, 22),
                'request_date_to': date(2022, 3, 25),
            })
            leave.with_user(SUPERUSER_ID).action_approve()
            # No work entries exist yet
            self.assertTrue(leave.can_cancel, "The leave should still be cancellable")
            # can not create in the future
            self.richard_emp.version_id.generate_work_entries(date(2022, 3, 21), date(2022, 3, 25))
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
        start = date(2022, 8, 1)
        end = date(2022, 8, 31)
        self.contract_cdi.generate_work_entries(start, end)
        work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.jules_emp.id),
            ('date', '>=', start),
            ('date', '<=', end),
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
            ('date', '>=', start),
            ('date', '<=', end),
        ])
        self.assertEqual(len(work_entries.work_entry_type_id), 2)

    def test_split_leaves_by_entry_type(self):
        entry_type_paid, entry_type_unpaid = self.env['hr.work.entry.type'].create([
            {'name': 'Paid leave', 'code': 'PAID', 'is_leave': True},
            {'name': 'Unpaid leave', 'code': 'UNPAID', 'is_leave': True},
        ])

        leave_type_paid, leave_type_unpaid = self.env['hr.leave.type'].create([{
            'name': 'Paid leave type',
            'requires_allocation': False,
            'request_unit': 'hour',
            'work_entry_type_id': entry_type_paid.id,
        },
        {
            'name': 'Unpaid leave type',
            'requires_allocation': False,
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

        (leave_paid | leave_unpaid).with_user(SUPERUSER_ID).action_approve()
        entries = self.contract_cdi._generate_work_entries(datetime(2024, 9, 10, 0, 0, 0), datetime(2024, 9, 10, 23, 59, 59))
        paid_leave_entry = entries.filtered_domain([('work_entry_type_id', '=', entry_type_paid.id)])
        unpaid_leave_entry = entries.filtered_domain([('work_entry_type_id', '=', entry_type_unpaid.id)])

        self.assertEqual(len(entries), 3, 'Leaves should have 1 entry per type')
        self.assertEqual(paid_leave_entry.duration, 1)
        self.assertEqual(unpaid_leave_entry.duration, 1)

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
            'full_time_required_hours': 40.0,
            'flexible_hours': True,
        })

        self.jules_emp.resource_calendar_id = flex_40h_calendar

        leave_paid = self.env['hr.leave'].create({
            'name': 'Paid leave',
            'employee_id': self.jules_emp.id,
            'holiday_status_id': leave_type_paid.id,
            'request_date_from': datetime(2024, 9, 10),
            'request_date_to': datetime(2024, 9, 13),
        })
        leave_paid.with_user(SUPERUSER_ID)._action_validate()

        entries = self.jules_emp.generate_work_entries(date(2024, 9, 9), date(2024, 9, 14))
        paid_leave_entry = entries.filtered_domain([('work_entry_type_id', '=', entry_type_paid.id)])
        self.assertEqual(len(paid_leave_entry), 4, "Four work entries should be created for a flexible employee")
        self.assertEqual(sum(paid_leave_entry.mapped('duration')), 32, "The combined duration of the work entries for flexible employee should "
                                                                        "be number of days * hours per day")
