from datetime import UTC, date, datetime

from freezegun import freeze_time

from odoo import Command, fields
from odoo.libs.datetime import timezone
from odoo.tests import Form, HttpCase, new_test_user
from odoo.tests.common import tagged


@tagged("hr_attendance_overtime")
class TestHrAttendanceOvertime(HttpCase):
    @classmethod
    def setUpClass(cls):
        def set_calendar_and_tz(employee, tz):
            calendar = employee.resource_calendar_id.copy()
            calendar.write(
                {
                    "name": f"Default Calendar ({tz})",
                    "tz": tz,
                }
            )
            employee.resource_calendar_id = calendar

        super().setUpClass()
        cls.ruleset = cls.env["hr.attendance.overtime.ruleset"].create(
            {
                "name": "Ruleset schedule quantity",
                "rule_ids": [
                    Command.create(
                        {
                            "name": "Rule schedule quantity",
                            "base_off": "quantity",
                            "expected_hours_from_contract": True,
                            "quantity_period": "day",
                        }
                    )
                ],
            }
        )

        cls.company = cls.env["res.company"].create(
            {
                "name": "SweatChipChop Inc.",
                "attendance_overtime_validation": "no_validation",
            }
        )
        cls.company.resource_calendar_id.tz = "Europe/Brussels"
        cls.company_1 = cls.env["res.company"].create(
            {
                "name": "Overtime Inc.",
            }
        )
        cls.company_1.resource_calendar_id.tz = "Europe/Brussels"
        cls.user = new_test_user(
            cls.env,
            login="fru",
            groups="base.group_user,hr_attendance.group_hr_attendance_manager",
            company_id=cls.company.id,
        ).with_company(cls.company)
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Marie-Edouard De La Court",
                "user_id": cls.user.id,
                "company_id": cls.company.id,
                "tz": "Europe/Brussels",
                "date_version": date(2020, 1, 1),
                "contract_date_start": date(2020, 1, 1),
                "resource_calendar_id": cls.company.resource_calendar_id.id,
                "ruleset_id": cls.ruleset.id,
            }
        )
        cls.other_employee = cls.env["hr.employee"].create(
            {
                "name": "Yolanda",
                "company_id": cls.company.id,
                "tz": "Europe/Brussels",
                "date_version": date(2020, 1, 1),
                "contract_date_start": date(2020, 1, 1),
                "resource_calendar_id": cls.company.resource_calendar_id.id,
                "ruleset_id": cls.ruleset.id,
            }
        )
        cls.jpn_employee = cls.env["hr.employee"].create(
            {
                "name": "Sacha",
                "company_id": cls.company.id,
                "tz": "Asia/Tokyo",
                "date_version": date(2020, 1, 1),
                "contract_date_start": date(2020, 1, 1),
                "resource_calendar_id": cls.company.resource_calendar_id.id,
                "ruleset_id": cls.ruleset.id,
            }
        )
        set_calendar_and_tz(cls.jpn_employee, "Asia/Tokyo")

        cls.honolulu_employee = cls.env["hr.employee"].create(
            {
                "name": "Susan",
                "company_id": cls.company.id,
                "tz": "Pacific/Honolulu",
                "date_version": date(2020, 1, 1),
                "contract_date_start": date(2020, 1, 1),
                "resource_calendar_id": cls.company.resource_calendar_id.id,
                "ruleset_id": cls.ruleset.id,
            }
        )
        set_calendar_and_tz(cls.honolulu_employee, "Pacific/Honolulu")

        cls.europe_employee = (
            cls.env["hr.employee"]
            .with_company(cls.company_1)
            .create(
                {
                    "name": "Schmitt",
                    "company_id": cls.company_1.id,
                    "tz": "Europe/Brussels",
                    "date_version": date(2020, 1, 1),
                    "contract_date_start": date(2020, 1, 1),
                    "resource_calendar_id": cls.company_1.resource_calendar_id.id,
                    "ruleset_id": cls.ruleset.id,
                }
            )
        )
        set_calendar_and_tz(cls.europe_employee, "Europe/Brussels")

        cls.no_contract_employee = cls.env["hr.employee"].create(
            {
                "name": "No Contract",
                "company_id": cls.company.id,
                "tz": "Europe/Brussels",
                "resource_calendar_id": cls.company.resource_calendar_id.id,
                "date_version": date(2020, 1, 1),
                "contract_date_start": False,
            }
        )
        cls.future_contract_employee = cls.env["hr.employee"].create(
            {
                "name": "Future contract",
                "company_id": cls.company.id,
                "tz": "Europe/Brussels",
                "resource_calendar_id": cls.company.resource_calendar_id.id,
                "date_version": date(2020, 1, 1),
                "contract_date_start": date(2030, 1, 1),
            }
        )

        cls.calendar_flex_40h = cls.env["resource.calendar"].create(
            {
                "name": "Flexible 40 hours/week",
                "company_id": cls.company.id,
                "hours_per_day": 8,
                "flexible_hours": True,
                "full_time_required_hours": 40,
            }
        )

        cls.flexible_employee = cls.env["hr.employee"].create(
            {
                "name": "Flexi",
                "company_id": cls.company.id,
                "tz": "UTC",
                "resource_calendar_id": cls.calendar_flex_40h.id,
                "date_version": date(2020, 1, 1),
                "contract_date_start": date(2020, 1, 1),
                "ruleset_id": cls.ruleset.id,
            }
        )

    def test_overtime_company_settings(self):
        self.company.write({"attendance_overtime_validation": "by_manager"})

        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": datetime(2021, 1, 4, 8, 0),
                "check_out": datetime(2021, 1, 4, 20, 0),
            }
        )

        self.assertEqual(attendance.overtime_status, "to_approve")
        self.assertAlmostEqual(attendance.validated_overtime_hours, 0, 2)
        self.assertEqual(attendance.employee_id.total_overtime, 0)

        attendance.action_approve_overtime()

        self.assertEqual(attendance.overtime_status, "approved")
        self.assertAlmostEqual(attendance.validated_overtime_hours, 3, 2)
        self.assertAlmostEqual(attendance.employee_id.total_overtime, 3, 2)

        attendance.action_refuse_overtime()
        self.assertEqual(attendance.employee_id.total_overtime, 0, 0)

    def test_simple_overtime(self):
        checkin_am = self.env["hr.attendance"].create(
            {"employee_id": self.employee.id, "check_in": datetime(2021, 1, 4, 7, 0)}
        )
        self.env["hr.attendance"].create(
            {
                "employee_id": self.other_employee.id,
                "check_in": datetime(2021, 1, 4, 7, 0),
                "check_out": datetime(2021, 1, 4, 21, 0),
            }
        )

        overtime = self.env["hr.attendance.overtime.line"].search(
            [("employee_id", "=", self.employee.id), ("date", "=", date(2021, 1, 4))]
        )
        self.assertFalse(overtime, "No overtime record should exist for that employee")

        checkin_am.write({"check_out": datetime(2021, 1, 4, 11, 0)})

        checkin_pm = self.env["hr.attendance"].create(
            {"employee_id": self.employee.id, "check_in": datetime(2021, 1, 4, 12, 0)}
        )
        self.assertEqual(
            overtime.duration,
            0,
            "Overtime duration should be 0 when an attendance has not been checked out.",
        )
        checkin_pm.write({"check_out": datetime(2021, 1, 4, 17, 0)})
        overtime = self.env["hr.attendance.overtime.line"].search(
            [("employee_id", "=", self.employee.id), ("date", "=", date(2021, 1, 4))]
        )
        self.assertAlmostEqual(overtime.duration, 1)
        self.assertAlmostEqual(self.employee.total_overtime, 1)

    def test_overtime_weekend(self):
        self.env["hr.attendance.overtime.rule"].create(
            {
                "name": "Rule non working days",
                "base_off": "timing",
                "timing_type": "non_work_days",
                "ruleset_id": self.ruleset.id,
            }
        )

        self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": datetime(2021, 1, 2, 8, 0),
                "check_out": datetime(2021, 1, 2, 11, 0),
            }
        )

        overtime = self.env["hr.attendance.overtime.line"].search(
            [("employee_id", "=", self.employee.id), ("date", "=", date(2021, 1, 2))]
        )
        self.assertTrue(overtime, "Overtime should be created")
        self.assertEqual(overtime.duration, 3, "Should have 3 hours of overtime")
        self.assertEqual(
            self.employee.total_overtime, 3, "Should still have 3 hours of overtime"
        )

    def test_overtime_multiple(self):
        self.env["hr.attendance.overtime.rule"].create(
            {
                "name": "Rule non working days",
                "base_off": "timing",
                "timing_type": "non_work_days",
                "ruleset_id": self.ruleset.id,
            }
        )
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": datetime(2021, 1, 2, 8, 0),
                "check_out": datetime(2021, 1, 2, 19, 0),
            }
        )
        self.assertEqual(self.employee.total_overtime, 11)

        self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": datetime(2021, 1, 4, 7, 0),
                "check_out": datetime(2021, 1, 4, 17, 0),
            }
        )
        self.assertEqual(self.employee.total_overtime, 12)

        attendance.unlink()
        self.assertAlmostEqual(self.employee.total_overtime, 1, 2)

    def test_overtime_change_employee(self):
        Attendance = self.env["hr.attendance"]
        attendance = Attendance.create(
            {
                "employee_id": self.employee.id,
                "check_in": datetime(2021, 1, 4, 7, 0),
                "check_out": datetime(2021, 1, 4, 18, 0),
            }
        )

        self.assertEqual(self.employee.total_overtime, 2)
        self.assertEqual(self.other_employee.total_overtime, 0)

        self.other_employee.ruleset_id = self.ruleset
        Attendance.create(
            {
                "employee_id": self.other_employee.id,
                "check_in": datetime(2021, 1, 4, 7, 0),
                "check_out": datetime(2021, 1, 4, 18, 0),
            }
        )
        attendance.unlink()
        self.assertEqual(self.other_employee.total_overtime, 2)
        self.assertEqual(self.employee.total_overtime, 0)

    def test_overtime_far_timezones(self):
        (self.jpn_employee | self.honolulu_employee).ruleset_id = self.ruleset
        self.env["hr.attendance"].create(
            {
                "employee_id": self.jpn_employee.id,
                "check_in": datetime(2021, 1, 4, 1, 0),
                "check_out": datetime(2021, 1, 4, 12, 0),
            }
        )

        self.env["hr.attendance"].create(
            {
                "employee_id": self.honolulu_employee.id,
                "check_in": datetime(2021, 1, 4, 17, 0),
                "check_out": datetime(2021, 1, 5, 4, 0),
            }
        )
        self.assertAlmostEqual(self.jpn_employee.total_overtime, 2, 2)
        self.assertAlmostEqual(self.honolulu_employee.total_overtime, 2, 2)

    def test_overtime_unclosed(self):
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": datetime(2021, 1, 4, 8, 0),
            }
        )
        overtime = self.env["hr.attendance.overtime.line"].search(
            [("employee_id", "=", self.employee.id)]
        )
        self.assertFalse(overtime, "Overtime entry should not exist at this point.")
        attendance.write(
            {
                "check_out": datetime(2021, 1, 4, 20, 0),
            }
        )
        overtime = self.env["hr.attendance.overtime.line"].search(
            [("employee_id", "=", self.employee.id)]
        )
        self.assertTrue(overtime, "An overtime entry should have been created.")
        self.assertEqual(overtime.duration, 3, "User should have 3 hours of overtime.")

    def test_employer_tolerance_suppresses_overtime_under_it(self):
        self.ruleset.rule_ids[0].employer_tolerance = 10 / 60
        self.env["hr.attendance"].create(
            [
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2021, 1, 4, 6, 55),
                    "check_out": datetime(2021, 1, 4, 11, 0),
                },
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2021, 1, 4, 12, 0),
                    "check_out": datetime(2021, 1, 4, 16, 5),
                },
            ]
        )
        overtime = self.env["hr.attendance.overtime.line"].search(
            [("employee_id", "=", self.employee.id)]
        )
        self.assertFalse(
            overtime, "No overtime should be counted because of the threshold."
        )

        self.ruleset.rule_ids[0].employer_tolerance = 4 / 60
        self.ruleset.action_regenerate_overtimes()

        overtime = self.env["hr.attendance.overtime.line"].search(
            [("employee_id", "=", self.employee.id)]
        )
        self.assertTrue(
            overtime,
            "Overtime entry should exist since the threshold has been lowered.",
        )
        self.assertAlmostEqual(
            overtime.duration,
            10 / 60,
            places=2,
            msg="Overtime should be equal to 10 minutes.",
        )

    def test_overtime_lunch(self):
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": datetime(2021, 1, 4, 8, 0),
                "check_out": datetime(2021, 1, 4, 17, 0),
            }
        )
        self.assertEqual(
            self.employee.total_overtime,
            0,
            "There should be no overtime since the employee worked through the lunch period.",
        )

        attendance.check_in = datetime(2021, 1, 4, 7, 0)
        attendance.check_out = datetime(2021, 1, 4, 16, 0)
        self.assertEqual(
            self.employee.total_overtime,
            0,
            "There should be no overtime since the employee worked through the lunch period.",
        )

        attendance.check_in = datetime(2021, 1, 4, 9, 0)
        attendance.check_out = datetime(2021, 1, 4, 18, 0)
        self.assertEqual(
            self.employee.total_overtime,
            0,
            "There should be no overtime since the employee worked through the lunch period.",
        )

    def test_overtime_hours_inside_attendance(self):
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": datetime(2023, 1, 2, 8, 0),
                "check_out": datetime(2023, 1, 2, 21, 0),
            }
        )

        self.assertAlmostEqual(attendance.overtime_hours, 4, 2)

        overtime_1 = self.env["hr.attendance.overtime.line"].search(
            [
                ("employee_id", "=", self.employee.id),
                ("date", "=", datetime(2023, 1, 2)),
            ]
        )
        self.assertAlmostEqual(overtime_1.duration, 4, 2)

        m_attendance_1 = self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": datetime(2023, 1, 3, 8, 0),
                "check_out": datetime(2023, 1, 3, 19, 0),
            }
        )
        self.assertAlmostEqual(m_attendance_1.overtime_hours, 2, 2)

        m_attendance_2 = self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": datetime(2023, 1, 3, 19, 0),
                "check_out": datetime(2023, 1, 3, 20, 0),
            }
        )
        self.assertAlmostEqual(m_attendance_2.overtime_hours, 1, 2)

        m_attendance_3 = self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": datetime(2023, 1, 3, 21, 0),
                "check_out": datetime(2023, 1, 3, 23, 0),
            }
        )
        self.assertAlmostEqual(m_attendance_3.overtime_hours, 2, 2)

        overtime_2 = self.env["hr.attendance.overtime.line"].search(
            [
                ("employee_id", "=", self.employee.id),
                ("date", "=", datetime(2023, 1, 3)),
            ]
        )
        self.assertEqual(sum(overtime_2.mapped("duration")), 5)

        m_attendance_3.write({"check_out": datetime(2023, 1, 3, 22, 30)})

        self.assertEqual(m_attendance_3.overtime_hours, 1.5)

        m_attendance_2.unlink()
        m_attendance_1.write({"check_out": datetime(2023, 1, 3, 17, 0)})
        m_attendance_3.write({"check_out": datetime(2023, 1, 3, 21, 30)})
        self.assertEqual(m_attendance_3.overtime_hours, 0.5)

        self.europe_employee.ruleset_id = self.ruleset
        early_attendance = self.env["hr.attendance"].create(
            {
                "employee_id": self.europe_employee.id,
                "check_in": datetime(2024, 5, 27, 23, 30),
                "check_out": datetime(2024, 5, 28, 13, 30),
            }
        )

        self.assertAlmostEqual(early_attendance.overtime_hours, 5)

        overtime_record = self.env["hr.attendance.overtime.line"].search(
            [
                ("employee_id", "=", self.europe_employee.id),
                ("date", "=", datetime(2024, 5, 28)),
            ]
        )
        self.assertAlmostEqual(overtime_record.duration, 5)

        self.europe_employee.tz = "America/New_York"
        early_attendance2 = self.env["hr.attendance"].create(
            {
                "employee_id": self.europe_employee.id,
                "check_in": datetime(2024, 5, 30, 3, 0),
                "check_out": datetime(2024, 5, 30, 16, 0),
            }
        )

        self.assertAlmostEqual(early_attendance2.overtime_hours, 4)
        overtime_record2 = self.env["hr.attendance.overtime.line"].search(
            [
                ("employee_id", "=", self.europe_employee.id),
                ("date", "=", datetime(2024, 5, 30)),
            ]
        )
        self.assertAlmostEqual(overtime_record2.duration, 4)

    @freeze_time("2024-02-01 23:00:00")
    def test_auto_check_out(self):
        self.company.write({"auto_check_out": True, "auto_check_out_tolerance": 1})
        self.env["hr.attendance"].create(
            [
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2024, 2, 1, 8, 0),
                    "check_out": datetime(2024, 2, 1, 11, 0),
                },
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2024, 2, 1, 11, 0),
                    "check_out": datetime(2024, 2, 1, 13, 0),
                },
            ]
        )

        attendance_utc_pending = self.env["hr.attendance"].create(
            {"employee_id": self.employee.id, "check_in": datetime(2024, 2, 1, 14, 0)}
        )

        attendance_utc_pending_within_allotted_hours = self.env["hr.attendance"].create(
            {
                "employee_id": self.europe_employee.id,
                "check_in": datetime(2024, 2, 1, 20, 0, 0),
            }
        )

        attendance_utc_done = self.env["hr.attendance"].create(
            {
                "employee_id": self.other_employee.id,
                "check_in": datetime(2024, 2, 1, 8, 0),
                "check_out": datetime(2024, 2, 1, 17, 0),
            }
        )

        attendance_jpn_pending = self.env["hr.attendance"].create(
            {
                "employee_id": self.jpn_employee.id,
                "check_in": datetime(2024, 2, 1, 12, 0),
            }
        )

        attendance_flexible_pending = self.env["hr.attendance"].create(
            {
                "employee_id": self.flexible_employee.id,
                "check_in": datetime(2024, 2, 1, 12, 0),
            }
        )

        self.assertEqual(attendance_utc_pending.check_out, False)
        self.assertEqual(attendance_utc_pending_within_allotted_hours.check_out, False)
        self.assertEqual(attendance_utc_done.check_out, datetime(2024, 2, 1, 17, 0))
        self.assertEqual(attendance_jpn_pending.check_out, False)
        self.assertEqual(attendance_flexible_pending.check_out, False)

        self.env["hr.attendance"]._cron_auto_check_out()

        self.assertEqual(attendance_utc_pending.check_out, datetime(2024, 2, 1, 19, 0))
        self.assertEqual(attendance_utc_pending_within_allotted_hours.check_out, False)
        self.assertEqual(attendance_utc_done.check_out, datetime(2024, 2, 1, 17, 0))
        self.assertEqual(attendance_jpn_pending.check_out, datetime(2024, 2, 1, 21, 0))

        self.assertEqual(attendance_flexible_pending.check_out, False)

    @freeze_time("2024-02-1 23:00:00")
    def test_auto_check_out_more_one_day_delta(self):
        self.company.write({"auto_check_out": True, "auto_check_out_tolerance": 1})

        attendance_utc_pending = self.env["hr.attendance"].create(
            {"employee_id": self.employee.id, "check_in": datetime(2024, 1, 30, 8, 0)}
        )

        self.assertEqual(attendance_utc_pending.check_out, False)
        self.env["hr.attendance"]._cron_auto_check_out()
        self.assertEqual(attendance_utc_pending.check_out, datetime(2024, 1, 30, 18, 0))

    @freeze_time("2024-02-05 23:00:00")
    def test_auto_checkout_past_day(self):
        self.company.write(
            {
                "auto_check_out": True,
                "auto_check_out_tolerance": 1,
            }
        )
        attendance_utc_pending_7th_day = self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": datetime(2024, 2, 1, 14, 0),
            }
        )
        self.assertEqual(attendance_utc_pending_7th_day.check_out, False)
        self.env["hr.attendance"]._cron_auto_check_out()
        self.assertEqual(
            attendance_utc_pending_7th_day.check_out, datetime(2024, 2, 1, 23, 0)
        )

    @freeze_time("2024-02-2 20:00:00")
    def test_auto_check_out_calendar_tz(self):
        self.company.write({"auto_check_out": True, "auto_check_out_tolerance": 1})
        self.jpn_employee.resource_calendar_id.tz = "Asia/Tokyo"
        self.jpn_employee.resource_calendar_id.attendance_ids.filtered(
            lambda a: a.dayofweek == "4" and a.day_period in ["lunch", "afternoon"]
        ).unlink()

        attendances_jpn = self.env["hr.attendance"].create(
            [
                {
                    "employee_id": self.jpn_employee.id,
                    "check_in": datetime(2024, 2, 1, 6, 0),
                    "check_out": datetime(2024, 2, 1, 7, 0),
                },
                {
                    "employee_id": self.jpn_employee.id,
                    "check_in": datetime(2024, 2, 1, 21, 0),
                    "check_out": datetime(2024, 2, 1, 22, 0),
                },
                {
                    "employee_id": self.jpn_employee.id,
                    "check_in": datetime(2024, 2, 1, 23, 0),
                },
            ]
        )

        self.env["hr.attendance"]._cron_auto_check_out()
        self.assertEqual(
            attendances_jpn[2].check_out,
            datetime(2024, 2, 2, 3, 0),
            "Check-out after 4 hours (4 hours expected from calendar + 1 hours tolerance - 1 hour previous attendance)",
        )

    def test_auto_check_out_lunch_period(self):
        Attendance = self.env["hr.attendance"]
        self.company.write({"auto_check_out": True, "auto_check_out_tolerance": 1})
        morning, afternoon = Attendance.create(
            [
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2024, 1, 1, 8, 0),
                    "check_out": datetime(2024, 1, 1, 12, 0),
                },
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2024, 1, 1, 13, 0),
                },
            ]
        )

        with freeze_time("2024-01-01 22:00:00"):
            Attendance._cron_auto_check_out()
            # The schedule is written in Europe/Brussels, so its 12:00-13:00
            # lunch is 11:00-12:00 UTC and falls inside the 08:00-12:00 morning:
            # three worked hours, not four. This read 9 and cut at 18:00 while
            # the break was placed in the RESOURCE's zone (UTC here) instead of
            # the schedule's, which put it at 12:00-13:00 UTC -- outside both
            # attendances, deducted from neither.
            self.assertEqual(morning.worked_hours, 3)
            # The day is cut at exactly its budget: eight scheduled hours plus
            # an hour of tolerance. Three were worked in the morning, so six
            # more from the 13:00 UTC check-in.
            self.assertEqual(afternoon.worked_hours, 6)
            self.assertEqual(morning.worked_hours + afternoon.worked_hours, 9)
            self.assertEqual(afternoon.check_out, datetime(2024, 1, 1, 19, 0))

    def test_auto_check_out_two_weeks_calendar(self):
        Attendance = self.env["hr.attendance"]
        self.company.write({"auto_check_out": True, "auto_check_out_tolerance": 0})
        self.employee.resource_calendar_id.switch_calendar_type()
        self.employee.resource_calendar_id.attendance_ids.search(
            [
                ("dayofweek", "=", "2"),
                ("week_type", "=", "0"),
                ("day_period", "in", ["morning", "lunch"]),
            ]
        ).unlink()

        with freeze_time("2025-03-05 22:00:00"):
            att = Attendance.create(
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2025, 3, 5, 8, 0),
                }
            )
            Attendance._cron_auto_check_out()
            self.assertEqual(att.worked_hours, 4)
            self.assertEqual(att.check_out, datetime(2025, 3, 5, 12, 0))

        with freeze_time("2025-03-12 22:00:00"):
            att = Attendance.create(
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2025, 3, 12, 8, 0),
                }
            )
            Attendance._cron_auto_check_out()
            self.assertEqual(att.worked_hours, 8)
            self.assertEqual(att.check_out, datetime(2025, 3, 12, 17, 0))

    @freeze_time("2024-02-02 23:00:00")
    def test_auto_check_out_specific_time(self):
        """A fixed daily cut-off reaches the employees tolerance mode cannot.

        `_cron_auto_check_out_tolerance` measures an employee against their
        scheduled hours, so it filters on
        `resource_calendar_id.flexible_hours = False` -- which matches neither
        a flexible-schedule employee nor one with no calendar at all. Either of
        them who forgets to check out stays open for ever, and `hours_today`
        grows with the wall clock. The specific-time mode needs no schedule: it
        closes every open attendance at the company's cut-off, read in the
        employee's own zone.
        """
        self.company.write(
            {
                "auto_check_out": True,
                "auto_check_out_mode": "specific_time",
                "auto_check_out_specific_time": 20.0,
            }
        )
        # `_schedule_tz` prefers the version's own `tz` over the calendar's, so
        # the employee is what has to move, not the calendar.
        self.flexible_employee.tz = "Asia/Tokyo"

        # 08:00 UTC on the 1st is 17:00 in Tokyo, before that day's 20:00
        # cut-off -- which fell at 11:00 UTC and is long past.
        overdue = self.env["hr.attendance"].create(
            {
                "employee_id": self.flexible_employee.id,
                "check_in": datetime(2024, 2, 1, 8, 0),
            }
        )
        # 22:00 UTC on the 2nd is 07:00 on the 3rd in Tokyo: that day's cut-off
        # is the evening still to come.
        not_due_yet = self.env["hr.attendance"].create(
            {
                "employee_id": self.jpn_employee.id,
                "check_in": datetime(2024, 2, 2, 22, 0),
            }
        )
        self.assertFalse(overdue.check_out)
        self.assertFalse(not_due_yet.check_out)

        self.env["hr.attendance"]._cron_auto_check_out()

        self.assertEqual(overdue.check_out, datetime(2024, 2, 1, 11, 0))
        self.assertEqual(overdue.out_mode, "auto_check_out")
        self.assertFalse(
            not_due_yet.check_out,
            "the cut-off for this attendance has not come round yet",
        )

    def test_overtime_hours_flexible_resource(self):
        self.flexible_employee.ruleset_id = self.ruleset
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": self.flexible_employee.id,
                "check_in": datetime(2023, 1, 2, 8, 0),
                "check_out": datetime(2023, 1, 2, 16, 0),
            }
        )
        self.assertEqual(
            attendance.overtime_hours,
            0,
            "There should be no overtime for the flexible resource.",
        )

        attendance.write(
            {
                "check_in": datetime(2023, 1, 3, 12, 0),
                "check_out": datetime(2023, 1, 3, 18, 0),
            }
        )
        self.assertAlmostEqual(
            attendance.overtime_hours,
            0,
            2,
            "There should be 0 hours of overtime for the flexible resource.",
        )

        attendance.write(
            {
                "check_in": datetime(2023, 1, 4, 10, 0),
                "check_out": datetime(2023, 1, 4, 22, 0),
            }
        )
        self.assertAlmostEqual(
            attendance.overtime_hours,
            4,
            2,
            "There should be 4 hours of overtime for the flexible resource.",
        )

    def test_overtime_hours_multiple_flexible_resources(self):
        self.flexible_employee.ruleset_id = self.ruleset

        attendance_1 = self.env["hr.attendance"].create(
            {
                "employee_id": self.flexible_employee.id,
                "check_in": datetime(2023, 1, 2, 8, 0),
                "check_out": datetime(2023, 1, 2, 12, 0),
            }
        )
        self.assertAlmostEqual(
            attendance_1.overtime_hours,
            0,
            2,
            "There should be -4 hours of overtime for the flexible resource.",
        )

        attendance_2 = self.env["hr.attendance"].create(
            {
                "employee_id": self.flexible_employee.id,
                "check_in": datetime(2023, 1, 2, 13, 0),
                "check_out": datetime(2023, 1, 2, 15, 0),
            }
        )
        self.assertEqual(
            attendance_1.overtime_hours,
            0,
            "There should be no overtime for the flexible resource.",
        )
        self.assertAlmostEqual(
            attendance_2.overtime_hours,
            0,
            2,
            "There should be 0 hours of overtime for the flexible resource.",
        )

        attendance_3 = self.env["hr.attendance"].create(
            {
                "employee_id": self.flexible_employee.id,
                "check_in": datetime(2023, 1, 2, 16, 0),
                "check_out": datetime(2023, 1, 2, 18, 0),
            }
        )
        self.assertEqual(
            attendance_1.overtime_hours,
            0,
            "There should be no overtime for the flexible resource.",
        )
        self.assertEqual(
            attendance_2.overtime_hours,
            0,
            "There should be no overtime for the flexible resource.",
        )
        self.assertEqual(
            attendance_3.overtime_hours,
            0,
            "There should be no overtime for the flexible resource.",
        )

    def test_overtime_hours_fully_flexible_resource(self):
        self.flexible_employee.resource_calendar_id = False

        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": self.flexible_employee.id,
                "check_in": datetime(2023, 1, 2, 8, 0),
                "check_out": datetime(2023, 1, 2, 16, 0),
            }
        )
        self.assertEqual(
            attendance.overtime_hours,
            0,
            "There should be no overtime for the fully flexible resource.",
        )

        attendance.write(
            {
                "check_in": datetime(2023, 1, 3, 16, 0),
                "check_out": datetime(2023, 1, 4, 9, 0),
            }
        )
        self.assertEqual(
            attendance.overtime_hours,
            0,
            "There should be no overtime for the fully flexible resource.",
        )

    def test_refuse_timeoff(self):
        self.company.write({"attendance_overtime_validation": "by_manager"})
        self.employee.tz = "Europe/Brussels"
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": datetime(2023, 1, 2, 8, 0),
                "check_out": datetime(2023, 1, 3, 12, 0),
            }
        )
        overtime = self.env["hr.attendance.overtime.line"].search(
            [
                ("employee_id", "=", self.employee.id),
            ]
        )
        self.assertItemsEqual(overtime.mapped("duration"), [6, 4])
        self.assertEqual(attendance.validated_overtime_hours, 0)
        overtime.action_approve()
        self.assertEqual(attendance.validated_overtime_hours, 10)
        self.assertEqual(attendance.overtime_hours, attendance.validated_overtime_hours)

        attendance.action_refuse_overtime()
        self.assertEqual(attendance.validated_overtime_hours, 0)

        attendances = self.env["hr.attendance"].create(
            [
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2025, 12, 18, 8, 0),
                    "check_out": datetime(2025, 12, 18, 11, 0),
                },
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2025, 12, 18, 12, 0),
                    "check_out": datetime(2025, 12, 19, 12, 0),
                },
            ]
        )
        overtimes = self.env["hr.attendance.overtime.line"].search(
            [
                ("employee_id", "=", self.employee.id),
                ("date", ">=", datetime(2025, 12, 18).date()),
            ]
        )
        self.assertItemsEqual(overtimes.mapped("duration"), [6, 4])
        self.assertEqual(sum(attendances.mapped("validated_overtime_hours")), 0)
        overtimes.action_approve()
        self.assertEqual(sum(attendances.mapped("validated_overtime_hours")), 10)
        self.assertEqual(
            sum(attendances.mapped("overtime_hours")),
            sum(attendances.mapped("validated_overtime_hours")),
        )

        attendances.action_refuse_overtime()
        self.assertEqual(sum(attendances.mapped("validated_overtime_hours")), 0)

    def test_no_validation_extra_hours_change(self):
        self.company.hr_attendance_config_id.attendance_overtime_validation = (
            "no_validation"
        )

        attendance = self.env["hr.attendance"]
        with Form(attendance) as attendance_form:
            attendance_form.employee_id = self.employee
            attendance_form.check_in = datetime(2023, 1, 2, 8, 0)
            attendance_form.check_out = datetime(2023, 1, 2, 18, 0)
        attendance = attendance_form.save()

        self.assertAlmostEqual(attendance.overtime_hours, 1, 2)
        self.assertAlmostEqual(attendance.validated_overtime_hours, 1, 2)

        attendance.linked_overtime_ids.manual_duration = previous = 0.5
        self.assertAlmostEqual(
            attendance.overtime_hours,
            previous,
            2,
            "the correction is what the attendance now reports",
        )
        self.assertAlmostEqual(
            attendance.validated_overtime_hours,
            previous,
            2,
            "and the approved figure agrees with it -- an attendance must not "
            "carry two extra-hours numbers that contradict each other",
        )

        self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": datetime(2023, 1, 4, 8, 0),
                "check_out": datetime(2023, 1, 4, 18, 0),
            }
        )
        self.assertEqual(
            attendance.validated_overtime_hours,
            previous,
            "Extra hours shouldn't be recomputed",
        )

    def _check_overtimes(self, overtimes, vals_list):
        self.assertEqual(len(overtimes), len(vals_list), "Wrong number of overtimes")
        for overtime, vals in zip(overtimes, vals_list, strict=True):
            for k, v in vals.items():
                self.assertEqual(overtime[k], v)

    def test_overtime_rule_timing(self):
        version = self.employee._get_version(date(2025, 8, 20))
        ruleset = self.env["hr.attendance.overtime.ruleset"].create(
            {
                "name": "Test Timing Ruleset",
                "rule_ids": [
                    Command.create(
                        {
                            "name": "Company Schedule",
                            "base_off": "timing",
                            "timing_type": "schedule",
                            "resource_calendar_id": self.company.resource_calendar_id.id,
                        }
                    ),
                    Command.create(
                        {
                            "name": "Naptime",
                            "base_off": "timing",
                            "timing_type": "work_days",
                            "timing_start": 14,
                            "timing_stop": 15,
                        }
                    ),
                ],
            }
        )

        version.ruleset_id = ruleset
        self.europe_employee.ruleset_id = ruleset

        self.env["hr.attendance"].create(
            {
                "employee_id": self.europe_employee.id,
                "check_in": datetime(2025, 8, 20, 5, 0),
                "check_out": datetime(2025, 8, 20, 14, 0),
            }
        )
        self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": datetime(2025, 8, 20, 7, 0),
                "check_out": datetime(2025, 8, 20, 16, 0),
            }
        )
        overtimes_by_employee = (
            self.env["hr.attendance.overtime.line"]
            .search(
                [
                    ("employee_id", "in", [self.employee.id, self.europe_employee.id]),
                ]
            )
            .grouped("employee_id")
        )
        self._check_overtimes(
            overtimes_by_employee.get(self.employee),
            [
                {
                    "date": date(2025, 8, 20),
                    "duration": 1,
                },
                {
                    "date": date(2025, 8, 20),
                    "duration": 1,
                },
            ],
        )

        self._check_overtimes(
            overtimes_by_employee.get(self.europe_employee),
            [
                {
                    "date": date(2025, 8, 20),
                    "duration": 1,
                },
                {
                    "date": date(2025, 8, 20),
                    "duration": 1,
                },
            ],
        )

    def test_overtime_rule_quantity(self):
        version = self.employee._get_version(date(2025, 8, 20))
        ruleset = self.env["hr.attendance.overtime.ruleset"].create(
            {
                "name": "Test Qty Ruleset",
                "rule_ids": [
                    Command.create(
                        {
                            "name": "> 9h/d",
                            "base_off": "quantity",
                            "quantity_period": "day",
                            "expected_hours_from_contract": False,
                            "expected_hours": 9,
                        }
                    ),
                    Command.create(
                        {
                            "name": "Weekly Overtime",
                            "base_off": "quantity",
                            "quantity_period": "week",
                            "expected_hours_from_contract": False,
                            "expected_hours": 40,
                        }
                    ),
                ],
            }
        )

        version.ruleset_id = ruleset

        self.env["hr.attendance"].create(
            [
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2025, 8, 18, 6, 0),
                    "check_out": datetime(2025, 8, 18, 17, 0),
                },
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2025, 8, 22, 6, 0),
                    "check_out": datetime(2025, 8, 22, 17, 0),
                },
                *[
                    {
                        "employee_id": self.employee.id,
                        "check_in": datetime(2025, 8, day, 6, 0),
                        "check_out": datetime(2025, 8, day, 15, 0),
                    }
                    for day in range(19, 22)
                ],
            ]
        )

        overtimes = self.env["hr.attendance.overtime.line"].search(
            [
                ("employee_id", "=", self.employee.id),
            ]
        )

        self.assertAlmostEqual(sum(ot.duration for ot in overtimes), 5.0, 2)
        self._check_overtimes(
            overtimes,
            [
                {
                    "date": date(2025, 8, 18),
                    "duration": 1,
                },
                {
                    "date": date(2025, 8, 22),
                    "duration": 3,
                },
                {
                    "date": date(2025, 8, 22),
                    "duration": 1,
                },
            ],
        )

    def test_overtime_rule_combined(self):
        pass

    def test_overtime_rule_timing_type_not_set(self):
        ruleset = self.env["hr.attendance.overtime.ruleset"].create(
            {
                "name": "Test Timing Ruleset",
                "rule_ids": [
                    Command.create(
                        {
                            "name": "Company Schedule",
                            "base_off": "timing",
                        }
                    ),
                ],
            }
        )

        self.assertEqual(
            ruleset.rule_ids.timing_type,
            "work_days",
            "Employee work Timing type should default to 'work_days' when not set.",
        )

    def test_employee_overtime_with_multiple_attendance_lines(self):
        # The kiosk reports "today" in the employee's own zone, which is
        # Brussels here; the server's date is behind it for two hours a day.
        employee_today = (
            fields.Datetime.now()
            .replace(tzinfo=UTC)
            .astimezone(timezone(self.employee._get_schedule_tz()))
            .date()
        )
        for _ in range(2):
            self.env["hr.attendance.overtime.line"].create(
                {
                    "employee_id": self.employee.id,
                    "date": employee_today,
                    "duration": 5,
                }
            )
        token = self.employee.company_id.hr_attendance_config_id.attendance_kiosk_key
        response = self.call_jsonrpc(
            "/hr_attendance/attendance_employee_data",
            {"token": token, "employee_id": self.employee.id},
        )
        self.assertEqual(response.get("hours_previously_today"), 0)
        self.assertEqual(response.get("hours_today"), 0)
        self.assertEqual(response.get("last_attendance_worked_hours"), 0)
        self.assertEqual(response.get("overtime_today"), 10)
        self.assertEqual(response.get("total_overtime"), 10)

    def test_overtime_with_public_holidays(self):
        with freeze_time("2025-11-11 12:00:00"):
            self.env.user.tz = "UTC"
            company_be = self.env["res.company"].create({"name": "Odoo BE"})
            company_de = self.env["res.company"].create({"name": "Odoo DE"})

            with Form(
                self.env["resource.schedule.exception"].with_company(company_be)
            ) as holiday_form:
                holiday_form.name = "Armistice Day"
                holiday_form.local_date_from = date(2025, 11, 11)
                holiday_form.save()

            ruleset_be = (
                self.env["hr.attendance.overtime.ruleset"]
                .with_company(company_be)
                .create(
                    {
                        "name": "Ruleset schedule timing",
                        "rule_ids": [
                            Command.create(
                                {
                                    "name": "Rule schedule timing",
                                    "base_off": "timing",
                                    "timing_type": "non_work_days",
                                    "timing_start": 0,
                                    "timing_stop": 24,
                                }
                            )
                        ],
                    }
                )
            )
            ruleset_de = (
                self.env["hr.attendance.overtime.ruleset"]
                .with_company(company_de)
                .create(
                    {
                        "name": "Ruleset schedule timing",
                        "rule_ids": [
                            Command.create(
                                {
                                    "name": "Rule schedule timing",
                                    "base_off": "timing",
                                    "timing_type": "non_work_days",
                                    "timing_start": 0,
                                    "timing_stop": 24,
                                }
                            )
                        ],
                    }
                )
            )

            employee_be = (
                self.env["hr.employee"]
                .with_company(company_be)
                .create(
                    {
                        "name": "Hans Belgian",
                        "ruleset_id": ruleset_be.id,
                    }
                )
            )
            employee_de = (
                self.env["hr.employee"]
                .with_company(company_de)
                .create(
                    {
                        "name": "Henry German",
                        "ruleset_id": ruleset_de.id,
                    }
                )
            )

            attendance_company_be = self.env["hr.attendance"].create(
                {
                    "employee_id": employee_be.id,
                    "check_in": datetime(2025, 11, 11, 8, 0),
                    "check_out": datetime(2025, 11, 11, 17, 0),
                }
            )
            attendance_company_de = self.env["hr.attendance"].create(
                {
                    "employee_id": employee_de.id,
                    "check_in": datetime(2025, 11, 11, 8, 0),
                    "check_out": datetime(2025, 11, 11, 17, 0),
                }
            )

            self.assertAlmostEqual(
                attendance_company_be.overtime_hours,
                9,
                2,
                "Employee from Company 1 should have overtime for working on a public holiday.",
            )
            self.assertAlmostEqual(
                attendance_company_de.overtime_hours,
                0,
                2,
                "Employee from Company 2 should not have overtime for working on a non-holiday day.",
            )

    def test_officer_access_on_overtime_records(self):
        user1 = new_test_user(
            self.env,
            login="user1",
            groups="hr_attendance.group_hr_attendance_officer",
            company_id=self.company.id,
        ).with_company(self.company)
        self.other_employee.attendance_manager_id = user1.id
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": self.other_employee.id,
                "check_in": datetime(2021, 1, 4, 8, 0),
                "check_out": datetime(2021, 1, 4, 20, 0),
            }
        )
        self.assertTrue(
            attendance.with_user(user1).linked_overtime_ids.rule_ids.has_access("read")
        )

    def test_attendance_overtime_with_timing_rule_cross_midnight(self):
        self.employee.ruleset_id.rule_ids.base_off = "timing"
        self.employee.ruleset_id.rule_ids.timing_start = 14
        self.employee.ruleset_id.rule_ids.timing_stop = 5
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": datetime(2021, 1, 4, 8, 0),
                "check_out": datetime(2021, 1, 4, 18, 0),
            }
        )

        self.assertEqual(attendance.worked_hours, 9.0)
        self.assertEqual(attendance.overtime_hours, 5.0)
        self.assertEqual(attendance.expected_hours, 4.0)

    def test_company_tolerance_multiple_attendances(self):
        self.employee.ruleset_id.rule_ids.employer_tolerance = 0.25
        (
            attendance_1,
            attendance_2,
            attendance_3,
            attendance_4,
            attendance_5,
            attendance_6,
        ) = self.env["hr.attendance"].create(
            [
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2023, 1, 4, 6, 0),
                    "check_out": datetime(2023, 1, 4, 7, 0),
                },
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2023, 1, 4, 11, 0),
                    "check_out": datetime(2023, 1, 4, 19, 30),
                },
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2023, 1, 5, 6, 0),
                    "check_out": datetime(2023, 1, 5, 7, 0),
                },
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2023, 1, 5, 11, 0),
                    "check_out": datetime(2023, 1, 5, 19, 14),
                },
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2023, 1, 6, 6, 44),
                    "check_out": datetime(2023, 1, 6, 11, 00),
                },
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2023, 1, 6, 12, 30),
                    "check_out": datetime(2023, 1, 6, 16, 44),
                },
            ]
        )
        expected = (0.0, 0.5, 0.0, 0.0, 0.0, 0.5)
        actual = (
            attendance_1.overtime_hours,
            attendance_2.overtime_hours,
            attendance_3.overtime_hours,
            attendance_4.overtime_hours,
            attendance_5.overtime_hours,
            attendance_6.overtime_hours,
        )

        for a, e in zip(actual, expected, strict=True):
            self.assertAlmostEqual(a, e)

    def test_employee_tolerance_multiple_attendances(self):
        self.employee.ruleset_id.rule_ids.employee_tolerance = 0.25
        self.employee.company_id.hr_attendance_config_id.absence_management = True
        self.employee.ruleset_id.rule_ids.company_id = self.employee.company_id
        (
            attendance_1,
            attendance_2,
            attendance_3,
            attendance_4,
            attendance_5,
            attendance_6,
        ) = self.env["hr.attendance"].create(
            [
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2023, 1, 4, 6, 0),
                    "check_out": datetime(2023, 1, 4, 7, 0),
                },
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2023, 1, 4, 11, 0),
                    "check_out": datetime(2023, 1, 4, 18, 30),
                },
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2023, 1, 5, 6, 0),
                    "check_out": datetime(2023, 1, 5, 7, 0),
                },
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2023, 1, 5, 11, 0),
                    "check_out": datetime(2023, 1, 5, 18, 54),
                },
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2023, 1, 6, 6, 44),
                    "check_out": datetime(2023, 1, 6, 11, 00),
                },
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2023, 1, 6, 12, 30),
                    "check_out": datetime(2023, 1, 6, 15, 44),
                },
            ]
        )

        expected = (0.0, -0.5, 0.0, 0.0, 0.0, -0.5)
        actual = (
            attendance_1.overtime_hours,
            attendance_2.overtime_hours,
            attendance_3.overtime_hours,
            attendance_4.overtime_hours,
            attendance_5.overtime_hours,
            attendance_6.overtime_hours,
        )

        for a, e in zip(actual, expected, strict=True):
            self.assertAlmostEqual(a, e)

    def test_check_linked_overtime_to_attendance(self):
        morning_att, afternoon_att = self.env["hr.attendance"].create(
            [
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2023, 1, 4, 7, 0),
                    "check_out": datetime(2023, 1, 4, 11, 0),
                },
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2023, 1, 4, 12, 0),
                    "check_out": datetime(2023, 1, 4, 19, 30),
                },
            ]
        )
        overtime_lines = (morning_att + afternoon_att).linked_overtime_ids
        self.assertFalse(morning_att.linked_overtime_ids)
        self.assertTrue(afternoon_att.linked_overtime_ids)
        self.assertEqual(overtime_lines._linked_attendances(), afternoon_att)

    def test_overtime_rule_timing_type_leave(self):
        with freeze_time("2025-11-10 12:00:00"):
            ruleset = self.env["hr.attendance.overtime.ruleset"].create(
                {
                    "name": "Ruleset timing leave",
                    "company_id": self.company.id,
                    "rule_ids": [
                        Command.create(
                            {
                                "name": "Rule timing leave",
                                "base_off": "timing",
                                "timing_type": "leave",
                                "timing_start": 0,
                                "timing_stop": 24,
                            }
                        )
                    ],
                }
            )
            employee = self.env["hr.employee"].create(
                {
                    "name": "On Leave Worker",
                    "company_id": self.company.id,
                    "tz": "UTC",
                    "date_version": date(2020, 1, 1),
                    "contract_date_start": date(2020, 1, 1),
                    "resource_calendar_id": self.company.resource_calendar_id.id,
                    "ruleset_id": ruleset.id,
                }
            )
            self.env["resource.schedule.exception"].create(
                {
                    "name": "Personal leave",
                    "resource_id": employee.resource_id.id,
                    "calendar_id": employee.resource_calendar_id.id,
                    "date_from": datetime(2025, 11, 10, 0, 0),
                    "date_to": datetime(2025, 11, 10, 23, 59, 59),
                }
            )
            attendance = self.env["hr.attendance"].create(
                {
                    "employee_id": employee.id,
                    "check_in": datetime(2025, 11, 10, 8, 0),
                    "check_out": datetime(2025, 11, 10, 17, 0),
                }
            )
            self.assertTrue(
                attendance.overtime_hours > 0,
                "Attendance recorded during a personal leave should be "
                "counted as overtime by a timing_type='leave' rule.",
            )
