from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import new_test_user
from odoo.tests.common import TransactionCase, tagged


def _eight_hour_calendar(env, company, tz, lunch=False):
    periods = [(8, 16, "morning")]
    if lunch:
        periods = [(8, 12, "morning"), (12, 13, "lunch"), (13, 17, "afternoon")]
    return env["resource.calendar"].create(
        {
            "name": f"Eight hours ({tz})",
            "company_id": company.id,
            "tz": tz,
            "attendance_ids": [
                Command.clear(),
                *(
                    Command.create(
                        {
                            "name": f"{day} {period}",
                            "dayofweek": str(index),
                            "hour_from": start,
                            "hour_to": stop,
                            "day_period": period,
                        }
                    )
                    for index, day in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri"])
                    for start, stop, period in periods
                ),
            ],
        }
    )


def _ruleset(env, company, periods=("day",)):
    return env["hr.attendance.overtime.ruleset"].create(
        {
            "name": "From the schedule",
            "company_id": company.id,
            "rule_ids": [
                Command.create(
                    {
                        "name": f"Beyond the scheduled {period}",
                        "base_off": "quantity",
                        "quantity_period": period,
                        "expected_hours_from_contract": True,
                        "paid": True,
                        "amount_rate": 1.0,
                    }
                )
                for period in periods
            ],
        }
    )


def _employee(env, company, calendar, ruleset, name="Audited", **extra):
    return env["hr.employee"].create(
        {
            "name": name,
            "company_id": company.id,
            "resource_calendar_id": calendar.id,
            "ruleset_id": ruleset.id,
            "date_version": date(2020, 1, 1),
            "contract_date_start": date(2020, 1, 1),
            **extra,
        }
    )


@tagged("post_install", "-at_install")
class TestPlainUserSystray(TransactionCase):
    """The systray and the session info run as the employee, who holds none of
    the attendance groups. Every field they need is officer-only, and the
    fork checks field groups on Python reads."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create(
            {"name": "Systray Ltd", "attendance_from_systray": True}
        )
        cls.user = new_test_user(
            cls.env,
            login="systray_plain",
            groups="base.group_user",
            company_id=cls.company.id,
        )
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Plain", "company_id": cls.company.id, "user_id": cls.user.id}
        )

    def _as_user(self):
        return self.employee.with_user(self.user).with_company(self.company)

    def test_a_plain_user_checks_in_and_out(self):
        checked_in = self._as_user()._attendance_action_change({"mode": "systray"})
        self.assertFalse(checked_in.env.su, "the caller gets back its own privilege")
        self.assertEqual(self.employee.attendance_state, "checked_in")
        self._as_user()._attendance_action_change({"mode": "systray"})
        self.assertEqual(self.employee.attendance_state, "checked_out")
        self.assertEqual(checked_in.in_mode, "systray")
        self.assertEqual(checked_in.out_mode, "systray")

    def test_a_plain_user_reads_their_systray_data(self):
        self._as_user()._attendance_action_change()
        data = self._as_user()._get_attendance_systray_data()
        self.assertEqual(data["attendance_state"], "checked_in")
        self.assertTrue(data["display_systray"])

    def test_no_employee_gives_no_data(self):
        self.assertEqual(self.env["hr.employee"]._get_attendance_systray_data(), {})


@tagged("post_install", "-at_install")
class TestOwnAttendanceForm(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Own Form Ltd"})
        cls.calendar = _eight_hour_calendar(cls.env, cls.company, "UTC")
        cls.ruleset = _ruleset(cls.env, cls.company)
        cls.user = new_test_user(
            cls.env,
            login="own_form",
            groups="base.group_user",
            company_id=cls.company.id,
        )
        cls.employee = _employee(
            cls.env, cls.company, cls.calendar, cls.ruleset, user_id=cls.user.id
        )
        cls.colleague = _employee(
            cls.env, cls.company, cls.calendar, cls.ruleset, name="Colleague"
        )
        cls.own, cls.theirs = cls.env["hr.attendance"].create(
            [
                {
                    "employee_id": employee.id,
                    "check_in": datetime(2026, 8, 31, 8, 0),
                    "check_out": datetime(2026, 8, 31, 19, 0),
                }
                for employee in (cls.employee, cls.colleague)
            ]
        )

    def test_the_form_of_ones_own_attendance_loads_its_overtime_lines(self):
        """`action_view_this_month_attendances` opens the attendance form, whose
        notebook lists the overtime lines; an employee must be able to see
        the lines of their own day."""
        values = self.own.with_user(self.user).web_read(
            {
                "linked_overtime_ids": {
                    "fields": {
                        "duration": {},
                        "status": {},
                        "rule_ids": {"fields": {"display_name": {}}},
                    }
                }
            }
        )
        self.assertEqual(len(values[0]["linked_overtime_ids"]), 1)
        self.assertEqual(values[0]["linked_overtime_ids"][0]["duration"], 3.0)
        self.assertTrue(
            values[0]["linked_overtime_ids"][0]["rule_ids"],
            "the form shows the applied rules as tags; own-read must reach the "
            "rule model too, not only the line",
        )

    def test_but_not_a_colleagues(self):
        with self.assertRaises(AccessError):
            self.theirs.with_user(self.user).linked_overtime_ids.read(["duration"])

    def test_and_cannot_change_them(self):
        with self.assertRaises(AccessError):
            self.own.with_user(self.user).linked_overtime_ids.write(
                {"manual_duration": 99}
            )


@tagged("post_install", "-at_install")
class TestRegenerationWindow(TransactionCase):
    """The lines regenerated with an attendance are those of the calendar
    days -- or weeks -- it shares, in the employee's own zone.

    Bounding the window by the UTC dates of `check_in`/`check_out` left an
    Auckland morning (Sunday evening in UTC) outside the day its afternoon
    was on: the afternoon's line survived the morning's regeneration, and a
    fresh line was added beside it on every save.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create(
            {"name": "Far East Ltd", "absence_management": True}
        )
        cls.calendar = _eight_hour_calendar(cls.env, cls.company, "Pacific/Auckland")
        cls.daily = _ruleset(cls.env, cls.company)
        cls.weekly = _ruleset(cls.env, cls.company, periods=("day", "week"))
        cls.Line = cls.env["hr.attendance.overtime.line"]

    def _lines(self, employee):
        return self.Line.search([("employee_id", "=", employee.id)], order="id")

    def _nz_monday(self, employee):
        # 2026-08-31 is a Monday; NZST is UTC+12, so 07:00 local is Sunday 19:00 UTC.
        morning = self.env["hr.attendance"].create(
            {
                "employee_id": employee.id,
                "check_in": datetime(2026, 8, 30, 19, 0),
                "check_out": datetime(2026, 8, 30, 23, 0),
            }
        )
        afternoon = self.env["hr.attendance"].create(
            {
                "employee_id": employee.id,
                "check_in": datetime(2026, 8, 31, 0, 0),
                "check_out": datetime(2026, 8, 31, 6, 0),
            }
        )
        return morning, afternoon

    def test_saving_the_morning_again_does_not_add_a_second_line(self):
        employee = _employee(self.env, self.company, self.calendar, self.daily)
        morning, afternoon = self._nz_monday(employee)
        # 4 + 6 hours against a scheduled 8: two over.
        self.assertEqual(self._lines(employee).mapped("duration"), [2.0])
        morning.write({"check_out": morning.check_out})
        self.assertEqual(self._lines(employee).mapped("duration"), [2.0])
        self.assertEqual(morning.overtime_hours + afternoon.overtime_hours, 2.0)
        morning.write({"check_out": datetime(2026, 8, 30, 23, 30)})
        self.assertEqual(self._lines(employee).mapped("duration"), [2.5])
        self.assertEqual(morning.overtime_hours + afternoon.overtime_hours, 2.5)

    def test_deleting_the_afternoon_recounts_the_day(self):
        employee = _employee(self.env, self.company, self.calendar, self.daily)
        morning, afternoon = self._nz_monday(employee)
        afternoon.unlink()
        self.assertEqual(self._lines(employee).mapped("duration"), [-4.0])
        self.assertEqual(morning.overtime_hours, -4.0)

    def test_moving_an_attendance_recounts_both_days(self):
        employee = _employee(self.env, self.company, self.calendar, self.daily)
        _morning, afternoon = self._nz_monday(employee)
        # Tuesday 12:00-18:00 local.
        afternoon.write(
            {
                "check_in": datetime(2026, 9, 1, 0, 0),
                "check_out": datetime(2026, 9, 1, 6, 0),
            }
        )
        by_date = {line.date: line.duration for line in self._lines(employee)}
        self.assertEqual(by_date, {date(2026, 8, 31): -4.0, date(2026, 9, 1): -2.0})

    def test_a_daily_ruleset_leaves_the_neighbouring_day_alone(self):
        """Regeneration deletes and recreates lines, and with them whatever a
        manager corrected. With no weekly rule, the day next door is not
        part of the sum and its line must survive untouched."""
        employee = _employee(self.env, self.company, self.calendar, self.daily)
        self._nz_monday(employee)
        monday_line = self._lines(employee)
        monday_line.manual_duration = 0.5
        self.env["hr.attendance"].create(
            {
                "employee_id": employee.id,
                "check_in": datetime(2026, 8, 31, 20, 0),
                "check_out": datetime(2026, 9, 1, 6, 0),
            }
        )
        self.assertTrue(monday_line.exists())
        self.assertEqual(monday_line.manual_duration, 0.5)

    def test_a_weekly_ruleset_recounts_the_week(self):
        employee = _employee(self.env, self.company, self.calendar, self.weekly)
        for offset in range(5):  # Mon 31 Aug .. Fri 4 Sep, 08:00-18:00 local
            check_out = datetime.combine(
                date(2026, 8, 31) + timedelta(days=offset), time(6, 0)
            )
            self.env["hr.attendance"].create(
                {
                    "employee_id": employee.id,
                    "check_in": check_out - timedelta(hours=10),
                    "check_out": check_out,
                }
            )
        total = sum(self._lines(employee).mapped("duration"))
        self.assertAlmostEqual(
            total,
            18.0,
            2,
            "two daily hours on Monday to Thursday, and all ten of Friday's beyond "
            "the 40-hour week: the weekly rule only reaches 40 hours when the "
            "week is regenerated as a whole",
        )
        windows = (
            self.env["hr.attendance"]
            .search([("employee_id", "=", employee.id)])[:1]
            ._overtime_windows()
        )
        self.assertEqual(
            windows[employee],
            (date(2026, 8, 31), date(2026, 9, 6)),
            "a weekly rule widens the window to the Monday-Sunday week",
        )

    def test_a_daily_ruleset_keeps_the_window_to_the_days(self):
        employee = _employee(self.env, self.company, self.calendar, self.daily)
        morning, _afternoon = self._nz_monday(employee)
        self.assertEqual(
            morning._overtime_windows()[employee],
            (date(2026, 8, 31), date(2026, 8, 31)),
        )


@tagged("post_install", "-at_install")
class TestDerivedFieldsFollowTheirSources(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Sources Ltd"})
        cls.ruleset = _ruleset(cls.env, cls.company)
        cls.no_lunch = _eight_hour_calendar(cls.env, cls.company, "UTC")
        cls.lunch = _eight_hour_calendar(cls.env, cls.company, "UTC", lunch=True)

    def test_last_attendance_follows_a_moved_check_in(self):
        employee = _employee(self.env, self.company, self.no_lunch, self.ruleset)
        first, second = self.env["hr.attendance"].create(
            [
                {
                    "employee_id": employee.id,
                    "check_in": datetime(2026, 8, 3, 8, 0),
                    "check_out": datetime(2026, 8, 3, 12, 0),
                },
                {
                    "employee_id": employee.id,
                    "check_in": datetime(2026, 8, 3, 13, 0),
                    "check_out": datetime(2026, 8, 3, 17, 0),
                },
            ]
        )
        self.assertEqual(employee.last_attendance_id, second)
        second.write(
            {
                "check_in": datetime(2026, 8, 3, 6, 0),
                "check_out": datetime(2026, 8, 3, 7, 0),
            }
        )
        self.assertEqual(
            employee.last_attendance_id,
            first,
            "the latest attendance is decided by check_in, so a change to "
            "check_in has to recompute it",
        )

    def test_worked_hours_follow_the_employee(self):
        without = _employee(self.env, self.company, self.no_lunch, self.ruleset)
        with_lunch = _employee(
            self.env, self.company, self.lunch, self.ruleset, name="Lunches"
        )
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": without.id,
                "check_in": datetime(2026, 8, 3, 8, 0),
                "check_out": datetime(2026, 8, 3, 17, 0),
            }
        )
        self.assertEqual(attendance.worked_hours, 9.0)
        attendance.employee_id = with_lunch
        self.assertEqual(
            attendance.worked_hours,
            8.0,
            "the lunch break comes from the employee's schedule, so the "
            "employee is a source of worked_hours",
        )


@tagged("post_install", "-at_install")
class TestApprovalVerdictsAgree(TransactionCase):
    def test_manage_all_approves_at_both_levels(self):
        company = self.env["res.company"].create({"name": "Verdict Ltd"})
        calendar = _eight_hour_calendar(self.env, company, "UTC")
        employee = _employee(self.env, company, calendar, _ruleset(self.env, company))
        attendance = self.env["hr.attendance"].create(
            {
                "employee_id": employee.id,
                "check_in": datetime(2026, 8, 3, 8, 0),
                "check_out": datetime(2026, 8, 3, 19, 0),
            }
        )
        manage_all = new_test_user(
            self.env,
            login="verdict_all",
            groups="hr_attendance.group_hr_attendance_user",
            company_id=company.id,
        )
        as_user = attendance.with_user(manage_all)
        self.assertTrue(as_user.is_manager)
        self.assertTrue(
            as_user.linked_overtime_ids.is_manager,
            "the line's approve button must show whenever the attendance's does",
        )


@tagged("post_install", "-at_install")
class TestAbsenceDetection(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create(
            {"name": "Absence Ltd", "absence_management": True}
        )
        cls.calendar = _eight_hour_calendar(cls.env, cls.company, "UTC")
        cls.ruleset = _ruleset(cls.env, cls.company)

        def make(name, **extra):
            return _employee(
                cls.env, cls.company, cls.calendar, cls.ruleset, name=name, **extra
            )

        cls.punctual = make("Punctual")
        cls.absent = make("Absent")
        cls.gone = make("Gone", contract_date_end=date(2026, 8, 15))
        # Tuesday 2026-09-01, exactly the scheduled eight hours.
        cls.env["hr.attendance"].create(
            {
                "employee_id": cls.punctual.id,
                "check_in": datetime(2026, 9, 1, 8, 0),
                "check_out": datetime(2026, 9, 1, 16, 0),
            }
        )

    def _technical(self, employee):
        return self.env["hr.attendance"].search(
            [("employee_id", "=", employee.id), ("in_mode", "=", "technical")]
        )

    def test_yesterday(self):
        with freeze_time("2026-09-02 03:00:00"):
            self.env["hr.attendance"]._cron_absence_detection()
        self.assertFalse(
            self._technical(self.punctual),
            "an employee with an attendance yesterday was there; that they "
            "earned no overtime line is not absence",
        )
        self.assertTrue(self._technical(self.absent))
        self.assertEqual(self.absent.total_overtime, -8.0)
        self.assertFalse(
            self._technical(self.gone),
            "a contract that ended weeks ago owes no attendance",
        )


@tagged("post_install", "-at_install")
class TestRuleConstraints(TransactionCase):
    def test_turning_off_the_schedule_needs_a_duration(self):
        ruleset = _ruleset(self.env, self.env.company)
        rule = ruleset.rule_ids
        with self.assertRaises(ValidationError):
            rule.expected_hours_from_contract = False


@tagged("post_install", "-at_install")
class TestOvertimeLineForeignKey(TransactionCase):
    """The overtime line is joined to its attendance by a real `attendance_id`,
    not by matching `time_start` against `check_in`."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "FK Ltd"})
        cls.calendar = _eight_hour_calendar(cls.env, cls.company, "UTC")
        cls.ruleset = _ruleset(cls.env, cls.company)
        cls.employee = _employee(cls.env, cls.company, cls.calendar, cls.ruleset)
        cls.attendance = cls.env["hr.attendance"].create(
            {
                "employee_id": cls.employee.id,
                "check_in": datetime(2026, 8, 31, 8, 0),
                "check_out": datetime(2026, 8, 31, 19, 0),
            }
        )
        cls.line = cls.env["hr.attendance.overtime.line"].search(
            [("employee_id", "=", cls.employee.id)]
        )

    def test_the_line_points_at_its_attendance(self):
        self.assertEqual(len(self.line), 1)
        self.assertEqual(self.line.attendance_id, self.attendance)
        self.assertEqual(self.attendance.linked_overtime_ids, self.line)

    def test_deleting_the_attendance_cascades_to_the_line(self):
        line_id = self.line.id
        self.attendance.unlink()
        self.assertFalse(
            self.env["hr.attendance.overtime.line"].browse(line_id).exists(),
            "the line has no reason to exist without its attendance",
        )

    def test_editing_a_line_moves_the_derived_fields_with_no_hand_rolled_marking(self):
        # 08:00-19:00 against an eight-hour schedule: eleven worked, three of
        # them extra by the rules.
        self.assertEqual(self.attendance.worked_hours, 11.0)
        self.assertEqual(self.line.duration, 3.0)

        self.line.manual_duration = 5.0
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(self.attendance.overtime_hours, 5.0)
        self.assertEqual(self.attendance.validated_overtime_hours, 5.0)
        # And `expected_hours` does NOT move: it is measured against `duration`,
        # what the rules computed, so a manager correcting the overtime cannot
        # restate how many hours the schedule expected. This assertion still
        # exercises the propagation the test is named for -- the field is
        # recomputed through the real relation either way -- it just pins the
        # value that does not depend on the correction. It read 6.0 while
        # `expected_hours` subtracted `manual_duration`, which made a twelve-
        # hour day's expectation follow whatever a manager typed.
        self.assertEqual(self.attendance.expected_hours, 8.0)

    def test_two_same_check_in_attendances_no_longer_collide(self):
        """The old join keyed on `time_start == check_in`; distinct employees
        with the same check-in used to be told apart only by employee. The FK
        removes the ambiguity entirely."""
        other = _employee(
            self.env, self.company, self.calendar, self.ruleset, name="Other"
        )
        other_att = self.env["hr.attendance"].create(
            {
                "employee_id": other.id,
                "check_in": datetime(2026, 8, 31, 8, 0),
                "check_out": datetime(2026, 8, 31, 19, 0),
            }
        )
        self.assertEqual(len(other_att.linked_overtime_ids), 1)
        self.assertNotEqual(other_att.linked_overtime_ids, self.line)
        self.assertEqual(other_att.linked_overtime_ids.attendance_id, other_att)


@tagged("post_install", "-at_install")
class TestApprovalSurvivesRegeneration(TransactionCase):
    """A manager's approval and manual correction survive a regeneration that
    leaves the line otherwise identical -- the compounding payoff of the real
    `attendance_id`: an unchanged line can be recognised across a delete and
    recreate."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create(
            {"name": "Survives Ltd", "attendance_overtime_validation": "by_manager"}
        )
        cls.calendar = _eight_hour_calendar(cls.env, cls.company, "UTC")
        cls.weekly = _ruleset(cls.env, cls.company, periods=("day", "week"))
        cls.employee = _employee(cls.env, cls.company, cls.calendar, cls.weekly)

    def _monday(self):
        # 2026-08-31 is a Monday; 08:00-18:00 = two hours over an 8h day.
        return self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": datetime(2026, 8, 31, 8, 0),
                "check_out": datetime(2026, 8, 31, 18, 0),
            }
        )

    def _tuesday(self):
        return self.env["hr.attendance"].create(
            {
                "employee_id": self.employee.id,
                "check_in": datetime(2026, 9, 1, 8, 0),
                "check_out": datetime(2026, 9, 1, 18, 0),
            }
        )

    def test_an_approval_survives_a_later_days_regeneration(self):
        monday = self._monday()
        line = monday.linked_overtime_ids
        self.assertEqual(line.status, "to_approve")
        line.action_approve()
        self.assertEqual(monday.overtime_status, "approved")
        # A Tuesday attendance in the same week regenerates Monday's line too
        # (weekly rule). Monday's overtime is unchanged, so the approval holds.
        self._tuesday()
        monday.invalidate_recordset()
        self.assertTrue(monday.linked_overtime_ids)
        self.assertEqual(
            monday.linked_overtime_ids.status,
            "approved",
            "regeneration is a system act; it must not silently un-approve a "
            "line whose overtime did not change",
        )

    def test_a_manual_correction_survives(self):
        monday = self._monday()
        monday.linked_overtime_ids.manual_duration = 5.0
        self._tuesday()
        monday.invalidate_recordset()
        self.assertEqual(monday.linked_overtime_ids.manual_duration, 5.0)
        self.assertEqual(monday.overtime_hours, 5.0)

    def test_a_real_change_resets_the_decision(self):
        monday = self._monday()
        monday.linked_overtime_ids.action_approve()
        # Editing Monday itself changes its overtime amount, so the approval
        # no longer describes what is there: it must fall back to to_approve.
        monday.write({"check_out": datetime(2026, 8, 31, 19, 0)})
        self.assertEqual(
            monday.linked_overtime_ids.status,
            "to_approve",
            "a changed amount is new overtime and needs a fresh decision",
        )


@tagged("post_install", "-at_install")
class TestAutoCheckOut(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create(
            {
                "name": "Auto Ltd",
                "auto_check_out": True,
                "auto_check_out_tolerance": 1.0,
            }
        )
        cls.calendar = _eight_hour_calendar(cls.env, cls.company, "UTC")
        cls.ruleset = _ruleset(cls.env, cls.company)
        cls.employee = _employee(cls.env, cls.company, cls.calendar, cls.ruleset)

    def test_an_over_long_open_attendance_is_closed_once_at_the_allowance(self):
        # Monday 2026-08-31, scheduled 08:00-16:00 (8h). Open since 08:00; the
        # cron runs at 20:00, well past 8h + 1h tolerance.
        with freeze_time("2026-08-31 20:00:00"):
            attendance = self.env["hr.attendance"].create(
                {
                    "employee_id": self.employee.id,
                    "check_in": datetime(2026, 8, 31, 8, 0),
                }
            )
            writes = []
            Attendance = type(self.env["hr.attendance"])
            original_write = Attendance.write

            def spy(records, vals):
                if records == attendance and "check_out" in vals:
                    writes.append(vals.get("out_mode"))
                return original_write(records, vals)

            with patch.object(Attendance, "write", spy):
                self.env["hr.attendance"]._cron_auto_check_out()
        self.assertEqual(attendance.out_mode, "auto_check_out")
        self.assertTrue(attendance.check_out)
        self.assertEqual(
            writes,
            ["auto_check_out"],
            "the attendance is closed in a single write, not first to end-of-day "
            "and then to the real cut-off",
        )
        # 8h scheduled + 1h tolerance = the attendance keeps 9 worked hours.
        self.assertAlmostEqual(attendance.worked_hours, 9.0, 2)
