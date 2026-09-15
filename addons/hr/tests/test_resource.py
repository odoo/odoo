from datetime import UTC, date, datetime

from odoo import Command
from odoo.fields import Date
from odoo.libs.datetime import timezone
from odoo.libs.intervals import Intervals
from odoo.tools.date_utils import get_intervals_hours

from .common import TestHrCommon


class TestResource(TestHrCommon):
    def test_resource_avatar_without_employee_uses_contact(self):
        partner = self.env["res.partner"].create({"name": "Resource contact"})
        resource = self.env["resource.resource"].create(
            {"name": "Independent resource", "partner_id": partner.id}
        )
        self.assertFalse(resource.employee_id)
        self.assertTrue(partner.avatar_128)
        self.assertEqual(resource.avatar_128, partner.avatar_128)

    def test_resource_avatar_follows_employee_avatar_changes(self):
        employee = self.env["hr.employee"].create({"name": "Avatar First"})
        resource = employee.resource_id
        initial = resource.avatar_128
        self.assertTrue(initial)
        self.assertEqual(initial, employee.avatar_128)
        replacement = self.env["res.partner"].create({"name": "Different Second"})
        employee.image_1920 = replacement._prepare_avatar_svg()
        self.assertNotEqual(initial, employee.avatar_128)
        self.assertEqual(resource.avatar_128, employee.avatar_128)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar_40h = cls.env["resource.calendar"].create(
            {"name": "Default calendar"}
        )
        cls.employee_niv = cls.env["hr.employee"].create(
            {
                "name": "Sharlene Rhodes",
                "departure_date": "2022-06-01",
                "resource_calendar_id": cls.calendar_40h.id,
            }
        )
        cls.employee_niv_create_date = "2021-01-01 10:00:00"
        cls.env.cr.execute(
            "UPDATE hr_employee SET create_date=%s WHERE id=%s",
            (cls.employee_niv_create_date, cls.employee_niv.id),
        )

        cls.calendar_richard = cls.env["resource.calendar"].create(
            {"name": "Calendar of Richard"}
        )
        cls.employee.resource_calendar_id = cls.calendar_richard

        cls.calendar_35h = cls.env["resource.calendar"].create(
            {
                "name": "35h calendar",
                "attendance_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Monday Morning",
                            "dayofweek": "0",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Monday Lunch",
                            "dayofweek": "0",
                            "hour_from": 12,
                            "hour_to": 13,
                            "day_period": "lunch",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Monday Evening",
                            "dayofweek": "0",
                            "hour_from": 13,
                            "hour_to": 16,
                            "day_period": "afternoon",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Tuesday Morning",
                            "dayofweek": "1",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Tuesday Lunch",
                            "dayofweek": "1",
                            "hour_from": 12,
                            "hour_to": 13,
                            "day_period": "lunch",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Tuesday Evening",
                            "dayofweek": "1",
                            "hour_from": 13,
                            "hour_to": 16,
                            "day_period": "afternoon",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Wednesday Morning",
                            "dayofweek": "2",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Wednesday Lunch",
                            "dayofweek": "2",
                            "hour_from": 12,
                            "hour_to": 13,
                            "day_period": "lunch",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Wednesday Evening",
                            "dayofweek": "2",
                            "hour_from": 13,
                            "hour_to": 16,
                            "day_period": "afternoon",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Thursday Morning",
                            "dayofweek": "3",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Thursday Lunch",
                            "dayofweek": "3",
                            "hour_from": 12,
                            "hour_to": 13,
                            "day_period": "lunch",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Thursday Evening",
                            "dayofweek": "3",
                            "hour_from": 13,
                            "hour_to": 16,
                            "day_period": "afternoon",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Friday Morning",
                            "dayofweek": "4",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Friday Lunch",
                            "dayofweek": "4",
                            "hour_from": 12,
                            "hour_to": 13,
                            "day_period": "lunch",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Friday Evening",
                            "dayofweek": "4",
                            "hour_from": 13,
                            "hour_to": 16,
                            "day_period": "afternoon",
                        },
                    ),
                ],
            }
        )

        cls.contract_cdd = cls.employee.version_id
        cls.contract_cdd.write(
            {
                "date_version": Date.to_date("2021-09-01"),
                "contract_date_start": Date.to_date("2021-09-01"),
                "contract_date_end": Date.to_date("2021-10-31"),
                "name": "First CDD Contract for Richard",
                "resource_calendar_id": cls.calendar_35h.id,
                "wage": 5000.0,
                "employee_id": cls.employee.id,
            }
        )
        cls.contract_cdi_values = {
            "date_version": Date.to_date("2021-11-01"),
            "contract_date_start": Date.to_date("2021-11-01"),
            "contract_date_end": False,
            "name": "CDI Contract for Richard",
            "resource_calendar_id": cls.calendar_richard.id,
            "wage": 5000.0,
            "employee_id": cls.employee.id,
        }

    def test_calendars_validity_within_period_default(self):
        calendars = self.employee_niv.resource_id._get_calendars_validity_within_period(
            datetime(2021, 7, 1, 8, 0, 0).replace(tzinfo=UTC),
            datetime(2021, 7, 30, 17, 0, 0).replace(tzinfo=UTC),
        )
        interval = Intervals(
            [
                (
                    datetime(2021, 7, 1, 8, 0, 0).replace(tzinfo=UTC),
                    datetime(2021, 7, 30, 17, 0, 0).replace(tzinfo=UTC),
                    self.env["resource.calendar.attendance"],
                )
            ]
        )

        self.assertEqual(
            1,
            len(calendars),
            "The dict returned by calendars validity should only have 1 entry",
        )
        self.assertEqual(
            1,
            len(calendars[self.employee_niv.resource_id.id]),
            "Niv should only have one calendar",
        )
        niv_entry = calendars[self.employee_niv.resource_id.id]
        niv_calendar = next(iter(niv_entry))
        self.assertEqual(niv_calendar, self.calendar_40h, "It should be Niv's Calendar")
        self.assertFalse(
            niv_entry[niv_calendar] - interval,
            "Interval should cover all calendar's validity",
        )
        self.assertFalse(
            interval - niv_entry[niv_calendar],
            "Calendar validity should cover all interval",
        )

    def test_calendars_validity_within_period_creation(self):
        calendars = self.employee_niv.resource_id._get_calendars_validity_within_period(
            datetime(2020, 12, 1, 8, 0, 0).replace(tzinfo=UTC),
            datetime(2021, 1, 31, 17, 0, 0).replace(tzinfo=UTC),
        )
        interval = Intervals(
            [
                (
                    datetime(2020, 12, 1, 8, 0, 0).replace(tzinfo=UTC),
                    datetime(2021, 1, 31, 17, 0, 0).replace(tzinfo=UTC),
                    self.env["resource.calendar.attendance"],
                )
            ]
        )
        niv_entry = calendars[self.employee_niv.resource_id.id]
        self.assertFalse(
            niv_entry[self.calendar_40h] - interval,
            "Interval should cover all calendar's validity",
        )
        self.assertFalse(
            interval - niv_entry[self.calendar_40h],
            "Calendar validity should cover all interval",
        )

    def test_availability_hr_infos_resource(self):
        user = self.env["res.users"].create(
            [
                {
                    "name": "Test user",
                    "login": "test",
                    "email": "test@odoo.perso",
                    "phone_ids": [
                        Command.create({"number": "+32488990011", "type": "landline"})
                    ],
                }
            ]
        )
        department = self.env["hr.department"].create(
            [
                {
                    "name": "QA",
                }
            ]
        )
        resource = self.env["resource.resource"].create(
            [
                {
                    "name": "Test resource",
                    "user_id": user.id,
                }
            ]
        )
        employee = self.env["hr.employee"].create(
            [
                {
                    "name": "Test employee",
                    "active": False,
                    "user_id": user.id,
                    "job_title": "Tester",
                    "department_id": department.id,
                    "work_email": "test@odoo.pro",
                    "phone_ids": [
                        Command.create({"number": "+32800100100", "type": "landline"})
                    ],
                    "resource_id": resource.id,
                }
            ]
        )
        for field in "email", "phone_ids", "im_status":
            self.assertEqual(resource[field], user[field])
        for field in (
            "job_title",
            "department_id",
            "work_email",
            "show_hr_icon_display",
            "hr_icon_display",
        ):
            self.assertEqual(resource[field], employee[field])

    def test_calendars_validity_within_period(self):
        self.employee.create_version(self.contract_cdi_values)
        tz = timezone(self.employee.tz)
        calendars = self.employee.resource_id._get_calendars_validity_within_period(
            datetime(2021, 10, 1, 0, 0, 0).replace(tzinfo=tz),
            datetime(2021, 12, 1, 0, 0, 0).replace(tzinfo=tz),
        )
        interval_35h = Intervals(
            [
                (
                    datetime(2021, 10, 1, 0, 0, 0).replace(tzinfo=tz),
                    datetime.combine(date(2021, 10, 31), datetime.max.time()).replace(
                        tzinfo=tz
                    ),
                    self.env["resource.calendar.attendance"],
                )
            ]
        )
        interval_40h = Intervals(
            [
                (
                    datetime(2021, 11, 1, 0, 0, 0).replace(tzinfo=tz),
                    datetime(2021, 12, 1, 0, 0, 0).replace(tzinfo=tz),
                    self.env["resource.calendar.attendance"],
                )
            ]
        )

        self.assertEqual(
            1,
            len(calendars),
            "The dict returned by calendars validity should only have 1 entry",
        )
        self.assertEqual(
            2,
            len(calendars[self.employee.resource_id.id]),
            "Jean should only have one calendar",
        )
        richard_entries = calendars[self.employee.resource_id.id]
        for calendar in richard_entries:
            self.assertTrue(
                calendar in (self.calendar_35h | self.calendar_richard),
                "Each calendar should be listed",
            )
            if calendar == self.calendar_35h:
                self.assertFalse(
                    richard_entries[calendar] - interval_35h,
                    "Interval 35h should cover all calendar 35h validity",
                )
                self.assertFalse(
                    interval_35h - richard_entries[calendar],
                    "Calendar 35h validity should cover all interval 35h",
                )
            elif calendar == self.calendar_richard:
                self.assertFalse(
                    richard_entries[calendar] - interval_40h,
                    "Interval 40h should cover all calendar 40h validity",
                )
                self.assertFalse(
                    interval_40h - richard_entries[calendar],
                    "Calendar 40h validity should cover all interval 40h",
                )

    def test_calendars_validity_follows_each_version_inside_one_contract(self):
        self.contract_cdd.contract_date_end = False
        self.employee.create_version(
            {
                "date_version": Date.to_date("2021-10-01"),
                "resource_calendar_id": self.calendar_richard.id,
            }
        )
        tz = timezone(self.employee.tz)
        start = datetime(2021, 9, 1).replace(tzinfo=tz)
        end = datetime(2021, 11, 1).replace(tzinfo=tz)
        no_attendance = self.env["resource.calendar.attendance"]
        september = Intervals(
            [
                (
                    start,
                    datetime(2021, 9, 30, 23, 59, 59).replace(tzinfo=tz),
                    no_attendance,
                )
            ]
        )
        october = Intervals(
            [(datetime(2021, 10, 1).replace(tzinfo=tz), end, no_attendance)]
        )

        validity = self.employee.resource_id._get_calendars_validity_within_period(
            start, end
        )[self.employee.resource_id.id]

        self.assertEqual(set(validity), {self.calendar_35h, self.calendar_richard})
        self.assertFalse(validity[self.calendar_35h] & october)
        self.assertFalse(validity[self.calendar_richard] & september)

    def test_queries(self):
        employees_test = self.env["hr.employee"].create(
            [
                {
                    "name": "Employee " + str(i),
                }
                for i in range(50)
            ]
        )
        for emp in employees_test:
            self.contract_cdd.copy({"employee_id": emp.id})
            self.contract_cdi_values["employee_id"] = emp.id
            self.employee.create_version(self.contract_cdi_values)

        start = datetime(2021, 9, 1, 0, 0, 0).replace(tzinfo=UTC)
        end = datetime(2021, 11, 30, 23, 59, 59).replace(tzinfo=UTC)
        with self.assertQueryCount(165):
            work_intervals, _ = (
                employees_test | self.employee
            ).resource_id._get_valid_work_intervals(start, end)

        self.assertEqual(len(work_intervals), 51)

    def test_get_valid_work_intervals(self):
        self.employee.create_version(self.contract_cdi_values)
        start = datetime(2021, 10, 24, 2, 0, 0).replace(
            tzinfo=timezone(self.employee.tz)
        )
        end = datetime(2021, 11, 6, 23, 59, 59).replace(
            tzinfo=timezone(self.employee.tz)
        )
        work_intervals, _ = self.employee.resource_id._get_valid_work_intervals(
            start, end
        )
        sum_work_intervals = get_intervals_hours(
            work_intervals[self.employee.resource_id.id]
        )
        self.assertEqual(
            75,
            sum_work_intervals,
            "Sum of the work intervals for the employee should be 35h+40h = 75h",
        )

    def test_multi_contract_attendance(self):
        date_from = datetime(2021, 10, 1, 0, 0, 0).replace(tzinfo=UTC)
        date_to = datetime(2021, 11, 30, 0, 0, 0).replace(tzinfo=UTC)

        attendances = self.employee._get_calendar_attendances(date_from, date_to)
        self.assertEqual(
            21 * 7,
            attendances["hours"],
            "Attendances should only include running or finished contracts.",
        )

        self.employee.create_version(self.contract_cdi_values)

        attendances = self.employee._get_calendar_attendances(date_from, date_to)
        self.assertEqual(
            21 * 7 + 21 * 8,
            attendances["hours"],
            "Attendances should add up multiple contracts with varying work weeks.",
        )

    def test_alter_resource_calendar_of_resouce(self):
        self.assertEqual(
            self.employee.resource_calendar_id, self.employee.resource_id.calendar_id
        )
        self.assertEqual(
            self.employee.version_id.resource_calendar_id,
            self.employee.resource_id.calendar_id,
        )
        # The version is the schedule's only writer; the resource follows it.
        self.employee.version_id.resource_calendar_id = self.calendar_40h
        self.assertEqual(self.employee.resource_id.calendar_id, self.calendar_40h)
        self.assertEqual(self.employee.resource_calendar_id, self.calendar_40h)
