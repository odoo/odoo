# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta

from odoo.tests import HttpCase, tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged("post_install", "-at_install")
class TestCalendarResizeTour(HttpCase, TestHrHolidaysCommon):
    def test_full_day_leave_resizable_in_month(self):
        # A full-day leave that stays in 'confirm' (manager validation) so the
        # employee may reschedule it and the calendar lets it be edited.
        leave_type = self.env["hr.work.entry.type"].create(
            {
                "name": "Resize tour type",
                "code": "RESIZE_TOUR",
                "requires_allocation": False,
                "leave_validation_type": "manager",
                "request_unit": "day",
                "unit_of_measure": "day",
            }
        )
        # Next Mon-Thu from today: future (so it is reschedulable), within the month
        # grid currently displayed, and with target+1 also a working day.
        target = date.today() + timedelta(days=1)
        while target.weekday() >= 4:
            target += timedelta(days=1)
        leave = (
            self.env["hr.leave"]
            .with_user(self.user_employee_id)
            .create(
                {
                    "name": "Resize me",
                    "employee_id": self.employee_emp_id,
                    "work_entry_type_id": leave_type.id,
                    "request_date_from": target,
                    "request_date_to": target,
                }
            )
        )
        self.assertEqual(leave.state, "confirm")
        self.assertTrue(leave.with_user(self.user_employee_id).can_reschedule)

        self.start_tour("/odoo", "time_off_resize_month_tour", login="enguerran")

        # The tour dragged the end border one day to the right: the resize must have
        # actually written through to the leave.
        leave.invalidate_recordset()
        self.assertEqual(
            leave.request_date_to,
            target + timedelta(days=1),
            "Resizing the leave in month view should extend it by one day",
        )

    def test_half_day_leave_resizable_in_month(self):
        # "half_day" is a unit (AM/PM endpoints), not a half-day-long leave: a
        # half-day leave is (half-)day-measured and must resize on the month grid by
        # whole days, exactly like a full-day one. A single-day half-day leave is
        # under 24h, so this also exercises the all-day remap that gives it a handle.
        leave_type = self.env["hr.work.entry.type"].create(
            {
                "name": "Resize tour half day",
                "code": "RESIZE_TOUR_HD",
                "requires_allocation": False,
                "leave_validation_type": "manager",
                "request_unit": "half_day",
                "unit_of_measure": "day",
            }
        )
        target = date.today() + timedelta(days=1)
        while target.weekday() >= 4:
            target += timedelta(days=1)
        leave = (
            self.env["hr.leave"]
            .with_user(self.user_employee_id)
            .create(
                {
                    "name": "Resize me",
                    "employee_id": self.employee_emp_id,
                    "work_entry_type_id": leave_type.id,
                    "request_date_from": target,
                    "request_date_to": target,
                    "request_date_from_period": "am",
                    "request_date_to_period": "pm",
                }
            )
        )
        self.assertEqual(leave.state, "confirm")
        self.assertEqual(leave.work_entry_type_request_unit, "half_day")
        self.assertTrue(leave.with_user(self.user_employee_id).can_reschedule)

        self.start_tour("/odoo", "time_off_resize_month_tour", login="enguerran")

        leave.invalidate_recordset()
        self.assertEqual(
            leave.request_date_to,
            target + timedelta(days=1),
            "A half-day-unit leave should resize by whole days in month view too",
        )
