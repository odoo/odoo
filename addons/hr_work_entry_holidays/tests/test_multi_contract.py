# # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from odoo.tests import tagged
from odoo.addons.hr_work_entry_holidays.tests.common import TestWorkEntryHolidaysBase


@tagged('work_entry_multi_contract')
@tagged('at_install', '-post_install')  # LEGACY at_install
class TestWorkEntryHolidaysMultiContract(TestWorkEntryHolidaysBase):

    def test_multi_contract_holiday(self):
        # Leave during second contract
        leave = self.create_leave(datetime(2015, 11, 17), datetime(2015, 11, 20), name="Doctor Appointment", employee_id=self.jules_emp.id)
        leave.action_approve()
        start = datetime(2015, 11, 1, 0, 0, 0)
        end_generate = datetime(2015, 11, 30, 23, 59, 59)
        work_entries = self.jules_emp.version_ids._generate_work_entries(start, end_generate)
        work_entries.action_validate()
        work_entries = work_entries.filtered(lambda we: we.version_id == self.contract_cdi)

        work = work_entries.filtered(lambda line: line.work_entry_type_id == self.env.ref('hr_work_entry.work_entry_type_attendance'))
        leave = work_entries.filtered(lambda line: line.work_entry_type_id == self.work_entry_type_leave)
        self.assertEqual(sum(work.mapped('duration')), 49, "It should be 49 hours of work this month for this contract")
        self.assertEqual(sum(leave.mapped('duration')), 28, "It should be 28 hours of leave this month for this contract")

    def test_leave_work_entry_covers_full_day_in_far_east_tz(self):
        """
        A one-day leave in Asia/Tokyo (UTC+9, attendance from 08:00) must produce 8h of leave work entries and replace
        the whole day's attendance.
        """
        self.calendar_40h.tz = "Asia/Tokyo"
        emp = self.env["hr.employee"].create({"name": "Kenji", "tz": "Asia/Tokyo"})
        version = self.env["hr.version"].create({
            "date_version": datetime(2026, 1, 1),
            "contract_date_start": datetime(2026, 1, 1),
            "name": "Contract for Kenji",
            "resource_calendar_id": self.calendar_40h.id,
            "wage": 5000.0,
            "employee_id": emp.id,
        })
        version._generate_work_entries(datetime(2026, 7, 1), datetime(2026, 7, 31, 23, 59, 59))
        leave = self.create_leave(datetime(2026, 7, 15), datetime(2026, 7, 15), employee_id=emp.id)
        # 08:00 Tokyo == 23:00 UTC the day before
        self.assertEqual(leave.date_from, datetime(2026, 7, 14, 23, 0))
        leave.action_approve()

        day_entries = self.env["hr.work.entry"].search([
            ("employee_id", "=", emp.id),
            ("date", "=", date(2026, 7, 15)),
        ])
        leave_entries = day_entries.filtered(lambda we: we.work_entry_type_id == self.work_entry_type_leave)
        self.assertEqual(sum(leave_entries.mapped("duration")), 8)
        self.assertFalse(day_entries - leave_entries, "The day's attendance entries should all be archived")

    def test_leave_split_over_two_generated_contracts_tz(self):
        """
        Leave spanning two contracts that both have generated work entries:
        each day is covered once, by the contract it belongs to, in any timezone.
        """
        for tz in ("Europe/Brussels", "Asia/Tokyo"):
            with self.subTest(tz=tz):
                calendar = self.calendar_40h.copy({"tz": tz})
                emp = self.env["hr.employee"].create({
                    "name": "Jules",
                    "tz": tz,
                })
                version_first = self.env["hr.version"].create({
                    "date_version": date(2026, 1, 1),
                    "contract_date_start": date(2026, 1, 1),
                    "name": "First Contract for Emp",
                    "resource_calendar_id": calendar.id,
                    "wage": 5000.0,
                    "employee_id": emp.id,
                })
                version_first.generate_work_entries(date(2026, 7, 1), date(2026, 7, 31))
                version_first.contract_date_end = date(2026, 7, 21)
                version_second = self.env["hr.version"].create({
                    "date_version": date(2026, 7, 22),
                    "contract_date_start": date(2026, 7, 22),
                    "name": "Second Contract for Emp",
                    "resource_calendar_id": calendar.id,
                    "wage": 5000.0,
                    "employee_id": emp.id,
                })
                version_second.generate_work_entries(date(2026, 7, 22), date(2026, 7, 31))

                leave = self.create_leave(
                    date(2026, 7, 15),
                    date(2026, 7, 22),
                    name="Doctor Appointment",
                    employee_id=emp.id,
                )
                leave.action_approve()

                leave_entries = self.env["hr.work.entry"].search([
                    ("employee_id", "=", emp.id),
                    ("work_entry_type_id", "=", self.work_entry_type_leave.id),
                ])
                first_entries = leave_entries.filtered(lambda we: we.version_id == version_first)
                second_entries = leave_entries - first_entries
                self.assertEqual(
                    sorted(first_entries.mapped("date")),
                    [date(2026, 7, 15), date(2026, 7, 16), date(2026, 7, 17), date(2026, 7, 20), date(2026, 7, 21)],
                    "The first contract should cover the leave days up to its end date",
                )
                self.assertEqual(
                    second_entries.mapped("date"),
                    [date(2026, 7, 22)],
                    "The second contract should only cover the leave days from its start date",
                )
                self.assertEqual(
                    sum(leave_entries.mapped("duration")),
                    48,
                    "Each of the 6 leave days should be counted once, for 8 hours",
                )
