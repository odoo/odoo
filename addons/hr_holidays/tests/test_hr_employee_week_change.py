# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta, date
from odoo import tests
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon
from odoo.tests.common import Form


@tests.tagged("post_install", "-at_install")
class TestHrHolidaysChangingEmployeeWeek(TestHrHolidaysCommon):
    def setUp(self):
        super().setUp()
        self.week_40_hour_per_week = self.env.ref("resource.resource_calendar_std")
        self.week_35_hour_per_week = self.env.ref("resource.resource_calendar_std_35h")
        self.compensatory_leave_type = self.env.ref("hr_holidays.holiday_status_comp")
        self.assertEqual(
            self.employee_emp.resource_calendar_id.id,
            self.week_40_hour_per_week.id,
            f"Expected default calendar to be 40h/week (found: {self.employee_emp.resource_calendar_id})",
        )
        self.alloc = (
            self.env["hr.leave.allocation"]
            .with_user(self.user_hrmanager.id)
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Compensatory allocation for employee",
                    "employee_id": self.employee_emp.id,
                    "holiday_status_id": self.compensatory_leave_type.id,
                    "allocation_type": "regular",
                    "holiday_type": "employee",
                    "number_of_days": 5,
                    # 'number_of_hours_display': 40,
                }
            )
        )
        self.alloc.action_approve()
        self.alloc = self.alloc.with_user(self.user_employee.id)
        today = date.today()
        next_monday = today + timedelta(days=-today.weekday(), weeks=1)
        leave_form = Form(
            self.env["hr.leave"].with_user(self.user_hrmanager),
            view="hr_holidays.hr_leave_view_form_manager",
        )
        leave_form.employee_id = self.employee_emp
        leave_form.holiday_status_id = self.compensatory_leave_type
        leave_form.request_date_from = next_monday
        leave_form.request_date_to = next_monday
        self.compensatory_day = leave_form.save()
        self.compensatory_day.action_approve()
        self.compensatory_day = self.compensatory_day.with_user(self.user_employee.id)

        self.assertEqual(self.alloc.number_of_hours_display, 40)
        self.assertEqual(self.alloc.hours_per_day, 8)
        self.assertEqual(self.alloc.max_leaves, 40)
        self.assertEqual(self.alloc.leaves_taken, 8)
        self.assertEqual(self.compensatory_day.number_of_hours_display, 8)
        self.assertEqual(self.compensatory_day.duration_display, "8 hours")
        self.assertEqual(self.compensatory_day.hours_per_day, 8)

        # avoid getting upset with computed field cached
        self.alloc.refresh()
        self.compensatory_day.refresh()

    def test_change_employee_week_keep_same_alloc_number_of_hours_display(self):
        """Acquired approved compensatory hours shouldn't change even
        employee contract change moving from 40 hours to 35 hours"""
        self.employee_emp.resource_calendar_id = self.week_35_hour_per_week
        self.assertEqual(self.alloc.number_of_hours_display, 40)

    def test_change_employee_week_keep_same_max_leaves(self):
        """Acquired approved compensatory hours shouldn't change even
        employee contract change moving from 40 hours to 35 hours"""
        self.employee_emp.resource_calendar_id = self.week_35_hour_per_week
        self.assertEqual(self.alloc.max_leaves, 40)

    def test_change_employee_week_keep_same_leaves_taken(self):
        """Acquired approved compensatory hours shouldn't change even
        employee contract change moving from 40 hours to 35 hours"""
        self.employee_emp.resource_calendar_id = self.week_35_hour_per_week
        self.assertEqual(self.alloc.leaves_taken, 8)

    def test_change_employee_week_keep_same_number_of_hours_display(self):
        """Acquired approved compensatory hours shouldn't change even
        employee contract change moving from 40 hours to 35 hours"""
        self.employee_emp.resource_calendar_id = self.week_35_hour_per_week
        self.assertEqual(self.compensatory_day.number_of_hours_display, 8)

    def test_change_employee_week_keep_same_duration_display(self):
        """Acquired approved compensatory hours shouldn't change even
        employee contract change moving from 40 hours to 35 hours"""
        self.employee_emp.resource_calendar_id = self.week_35_hour_per_week
        self.assertEqual(self.compensatory_day.duration_display, "8 hours")
        self.env.add_to_compute(
            self.compensatory_day._fields["duration_display"], self.compensatory_day
        )
        self.compensatory_day.recompute()
        self.assertEqual(self.compensatory_day.duration_display, "8 hours")

    def test_change_employee_week_hours_keep_same_number_of_hours_display(self):
        """Acquired approved compensatory hours shouldn't change even
        employee contract changing hours on hour earlier on monday on 40 hours/week"""
        self.employee_emp.resource_calendar_id.attendance_ids[0].hour_from -= 1
        self.employee_emp.resource_calendar_id.attendance_ids[0].hour_to -= 1
        self.assertEqual(self.compensatory_day.number_of_hours_display, 8)

    def test_change_employee_week_keep_hours_same_duration_display(self):
        """Acquired approved compensatory hours shouldn't change even
        employee contract changing hours on hour earlier on monday on 40 hours/week"""
        self.employee_emp.resource_calendar_id.attendance_ids[0].hour_from -= 1
        self.employee_emp.resource_calendar_id.attendance_ids[0].hour_to -= 1
        self.assertEqual(self.compensatory_day.duration_display, "8 hours")
        self.env.add_to_compute(
            self.compensatory_day._fields["duration_display"], self.compensatory_day
        )
        self.compensatory_day.recompute()
        self.assertEqual(self.compensatory_day.duration_display, "8 hours")
