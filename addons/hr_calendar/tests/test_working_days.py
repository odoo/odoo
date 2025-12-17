# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests import tagged

from odoo.addons.hr_calendar.tests.common import TestHrContractCalendarCommon


@tagged("work_days")
@tagged("at_install", "-post_install")  # LEGACY at_install
class TestWorkingDaysWithVersion(TestHrContractCalendarCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_working_hours_employee_available_after_contract_start(self):
        """
        Assert that an employee with a contract and a fixed schedule is available according to their schedule.
        """
        work_days = self.env["res.partner"]._get_unusual_days(
            [self.partnerA.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )

        expected_days = {
            "2023-12-25": False,  # Monday
            "2023-12-26": False,  # Tuesday
            "2023-12-27": False,  # Wednesday
            "2023-12-28": False,  # Thursday
            "2023-12-29": False,  # Friday
            "2023-12-30": True,  # Saturday
            "2023-12-31": True,  # Sunday
        }
        self.assertEqual(work_days, expected_days)

    def test_working_hours_employee_unavailable_before_contract_start(self):
        """
        Assert that an employee is not available before their contract starts.
        """
        work_days = self.env["res.partner"]._get_unusual_days(
            [self.partnerA.id],
            datetime(2023, 11, 13).isoformat(),
            datetime(2023, 11, 19).isoformat(),
        )
        # Unavailable the whole weekend as they are not working at the company yet.
        expected_days = {
            "2023-11-13": True,  # Monday
            "2023-11-14": True,  # Tuesday
            "2023-11-15": True,  # Wednesday
            "2023-11-16": True,  # Thursday
            "2023-11-17": True,  # Friday
            "2023-11-18": True,  # Saturday
            "2023-11-19": True,  # Sunday
        }
        self.assertEqual(work_days, expected_days)

    def test_working_hours_2_emp_same_calendar(self):
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id]

        work_days = self.env["res.partner"]._get_unusual_days(
            [self.partnerA.id, self.partnerD.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        expected_days = {
            "2023-12-25": False,  # Monday
            "2023-12-26": False,  # Tuesday
            "2023-12-27": False,  # Wednesday
            "2023-12-28": False,  # Thursday
            "2023-12-29": False,  # Friday
            "2023-12-30": True,  # Saturday
            "2023-12-31": True,  # Sunday
        }
        self.assertEqual(work_days, expected_days)

    def test_working_hours_2_emp_contract_start(self):
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id]

        self.contractB.contract_date_start = datetime(2023, 12, 28)
        work_days = self.env["res.partner"]._get_unusual_days(
            [self.partnerA.id, self.partnerB.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        # Nothing on monday, tuesday and wednesday due to contractB. (start : thursday 2023/12/28)
        expected_days = {
            "2023-12-25": True,  # Monday
            "2023-12-26": True,  # Tuesday
            "2023-12-27": True,  # Wednesday
            "2023-12-28": False,  # Thursday
            "2023-12-29": False,  # Friday
            "2023-12-30": True,  # Saturday
            "2023-12-31": True,  # Sunday
        }
        self.assertEqual(work_days, expected_days)

    def test_working_hours_2_emp_contract_stop(self):
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id]

        self.contractB.date_end = datetime(2023, 12, 28)
        self.contractB.contract_date_end = datetime(2023, 12, 28)
        work_days = self.env["res.partner"]._get_unusual_days(
            [self.partnerA.id, self.partnerB.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        # Nothing on monday due to calendarB.
        # Nothing on Friday due to contractB (stop : thursday 2023/12/28)
        expected_days = {
            "2023-12-25": True,  # Monday
            "2023-12-26": False,  # Tuesday
            "2023-12-27": False,  # Wednesday
            "2023-12-28": False,  # Thursday
            "2023-12-29": True,  # Friday
            "2023-12-30": True,  # Saturday
            "2023-12-31": True,  # Sunday
        }
        self.assertEqual(work_days, expected_days)

    def test_working_hours_3_emp_different_calendar(self):
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id]

        work_days = self.env["res.partner"]._get_unusual_days(
            [self.partnerA.id, self.partnerB.id, self.partnerC.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        # Nothing on monday due to partnerB's calendar : calendar_2
        # Nothing before 15:00 due to partnerC's calendar : calendar_3
        # Nothing on tuesday and wednesday due to contractC. (start : thursday 2023/12/28)
        expected_days = {
            "2023-12-25": True,  # Monday
            "2023-12-26": True,  # Tuesday
            "2023-12-27": True,  # Wednesday
            "2023-12-28": False,  # Thursday
            "2023-12-29": False,  # Friday
            "2023-12-30": True,  # Saturday
            "2023-12-31": True,  # Sunday
        }
        self.assertEqual(work_days, expected_days)

    def test_working_hours_2_emp_same_calendar_different_timezone(self):
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id]

        self.contractD.resource_calendar_id = self.calendar_35h
        self.contractD.tz = "Europe/London"
        work_days = self.env["res.partner"]._get_unusual_days(
            [self.partnerA.id, self.partnerD.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        # calendar_35h_london_tz.tz = UTC, calendar_35h.tz = UTC +1
        expected_days = {
            "2023-12-25": False,  # Monday
            "2023-12-26": False,  # Tuesday
            "2023-12-27": False,  # Wednesday
            "2023-12-28": False,  # Thursday
            "2023-12-29": False,  # Friday
            "2023-12-30": True,  # Saturday
            "2023-12-31": True,  # Sunday
        }
        self.assertEqual(work_days, expected_days)

    def test_working_hours_split_correctly_with_negative_difference_in_timezones(self):
        """
        The working hours of a calendar are localized to the "viewer's"/currently logged in user's timezone.
        if employee A starts working at 08:00 in the timezone GMT+5 and employee B, working in timezone GMT+1, views the
        calendar they will see employee A starting at 04:00 as the difference between the two timezones is -4 hours and
        08:00 + (-4hrs) is 04:00.
        Additionally if a localization makes the workday of employee A start "yesterday" or ends "tomorrow", the working
        hours should be split across the "yesterday", "today" and "tomorrow" depending on the scenario.
        """
        self.contractD.resource_calendar_id = self.sunday_morning_calendar
        self.contractD.tz = "Asia/Ashgabat"
        # "viewer"/self.env.user.tz = "Etc/GMT+1"
        work_days = self.env["res.partner"]._get_unusual_days(
            self.partnerD.ids,
            datetime(2023, 12, 29).isoformat(),  # Friday
            datetime(2024, 1, 1).isoformat(),  # Monday
        )
        # sunday_morning_calendar.tz = GMT+5, viewers_calendar.tz = GMT +1, difference = 4 hours "back in time"
        expected_days = {
            "2023-12-29": True,  # Friday
            "2023-12-30": False,  # Saturday
            "2023-12-31": False,  # Sunday
            "2024-01-01": True,  # Monday
        }
        self.assertEqual(work_days, expected_days)

    def test_split_working_hours_with_negative_difference_in_timezone_returns_relevant_portion(self):
        """
        If a working hours span across two days because of timezone difference then only return the working hours for
        the requested days.
        As an example if someone is working from 00:00 to 08:00 in GMT+5 and the working hours are viewed from GMT+1
        it should show working hours from 20:00 - 23:59 yesterday and 00:00 - 04:00 today. However if the request is
        to only get working hours for today it should only return 00:00 - 04:00 and not 20:00 - 23:59
        """
        self.contractD.resource_calendar_id = self.sunday_morning_calendar
        self.contractD.tz = "Asia/Ashgabat"

        work_days = self.env["res.partner"]._get_unusual_days(
            self.partnerD.ids,
            datetime(2023, 12, 30).isoformat(),  # Saturday
            datetime(2023, 12, 30).isoformat(),  # Saturday
        )
        # sunday_morning_calendar.tz = GMT-8, viewers_calendar.tz = GMT +1, difference = 9 hours "forwards in time"
        expected_days = {
            "2023-12-30": False,  # Monday
        }
        self.assertEqual(work_days, expected_days)

        work_days = self.env["res.partner"]._get_unusual_days(
            self.partnerD.ids,
            datetime(2023, 12, 31).isoformat(),  # Sunday
            datetime(2023, 12, 31).isoformat(),  # Sunday
        )
        # sunday_morning_calendar.tz = GMT-8, viewers_calendar.tz = GMT +1, difference = 9 hours "forwards in time"
        expected_days = {
            "2023-12-31": False,  # Sunday
        }
        self.assertEqual(work_days, expected_days)

    def test_working_hours_split_correctly_with_positive_difference_in_timezones(self):
        """
        The working hours of a calendar are localized to the "viewer's"/currently logged in user's timezone.
        If employee A starts working at 08:00 in the timezone GMT-8 and employee B, working in timezone GMT+1, views the
        calendar they will see employee A starting at 17:00 as the difference between the two timezones is 9 hours and
        08:00 + 9hrs is 17:00.
        Additionally if a localization makes the workday of employee A start "yesterday" or ends "tomorrow", the working
        hours should be split across the "yesterday", "today" and "tomorrow" depending on the scenario.
        """
        self.contractD.resource_calendar_id = self.sunday_afternoon_calendar
        self.contractD.tz = "America/Los_Angeles"
        # "viewer"/self.env.user.tz = "Etc/GMT+1"
        work_days = self.env["res.partner"]._get_unusual_days(
            self.partnerD.ids,
            datetime(2023, 12, 29).isoformat(),  # Friday
            datetime(2024, 1, 1).isoformat(),  # Monday
        )
        # sunday_afternoon_calendar.tz = GMT-8, viewers_calendar.tz = GMT +1, difference = 9 hours "forwards in time"
        expected_days = {
            "2023-12-29": True,  # Friday
            "2023-12-30": True,  # Saturday
            "2023-12-31": False,  # Sunday
            "2024-01-01": False,  # Monday
        }
        self.assertEqual(work_days, expected_days)

    def test_split_working_hours_with_positive_difference_in_timezone_returns_relevant_portion(self):
        """
        If a working hours span across two days because of timezone difference then only return the working hours for
        the requested days.
        As an example if someone is working from 08:00 to 17:00 in GMT-8 and the working hours are viewed from GMT+1
        it should show working hours from 17:00 - 23:59 yesterday and 00:00 - 02:00 today. However if the request is
        to only get working hours for today it should only return 17:00 - 23:59 and not 00:00 - 02:00
        """
        self.contractD.resource_calendar_id = self.sunday_afternoon_calendar
        self.contractD.tz = "America/Los_Angeles"

        work_days = self.env["res.partner"]._get_unusual_days(
            self.partnerD.ids,
            datetime(2023, 12, 31).isoformat(),  # Sunday
            datetime(2023, 12, 31).isoformat(),  # Sunday
        )

        expected_days = {
            "2023-12-31": False,  # Sunday
        }
        self.assertEqual(work_days, expected_days)

        work_days = self.env["res.partner"]._get_unusual_days(
            self.partnerD.ids,
            datetime(2024, 1, 1).isoformat(),  # Monday
            datetime(2024, 1, 1).isoformat(),  # Monday
        )

        expected_days = {
            "2024-01-01": False,  # Monday
        }
        self.assertEqual(work_days, expected_days)

    def test_working_hours_with_employee_without_contract(self):
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id]

        work_days = self.env["res.partner"]._get_unusual_days(
            [self.partnerA.id, self.partnerE.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        # Employee E doesn't have a contract
        expected_days = {
            "2023-12-25": True,  # Monday
            "2023-12-26": True,  # Tuesday
            "2023-12-27": True,  # Wednesday
            "2023-12-28": True,  # Thursday
            "2023-12-29": True,  # Friday
            "2023-12-30": True,  # Saturday
            "2023-12-31": True,  # Sunday
        }
        self.assertEqual(work_days, expected_days)

    def test_working_hours_one_employee_with_two_contracts(self):
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id]

        # Contract from november
        self.env["hr.version"].create(
            {
                "date_version": datetime(2023, 11, 1),
                "contract_date_start": datetime(2023, 11, 1),
                "contract_date_end": datetime(2023, 11, 30),
                "name": "Contract november",
                "resource_calendar_id": self.calendar_35h_night.id,
                "wage": 5000.0,
                "employee_id": self.employeeA.id,
            },
        )
        work_days = self.env["res.partner"]._get_unusual_days(
            [self.partnerA.id],
            datetime(2023, 11, 27).isoformat(),
            datetime(2023, 12, 3).isoformat(),
        )
        expected_days = {
            "2023-11-27": False,  # Monday
            "2023-11-28": False,  # Tuesday
            "2023-11-29": False,  # Wednesday
            "2023-11-30": False,  # Thursday
            "2023-12-01": False,  # Friday
            "2023-12-02": True,  # Saturday
            "2023-12-03": True,  # Sunday
        }
        self.assertEqual(work_days, expected_days)

    def test_multi_companies_2_employees_2_selected_companies(self):
        """
        INPUT:
        ======
        Employees                                   Companies
        employee B1 company A ---> 28h               [X] A    <- main company
        employee B2 company A ---> 35h night         [X] B

        OUTPUT:
        =======
        The schedule will be the union between 28h's and 35h night's schedule
        """
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id, self.company_B.id]

        work_days = self.env["res.partner"]._get_unusual_days(
            [self.partnerB.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        expected_days = {
            "2023-12-25": False,  # Monday
            "2023-12-26": False,  # Tuesday
            "2023-12-27": False,  # Wednesday
            "2023-12-28": False,  # Thursday
            "2023-12-29": False,  # Friday
            "2023-12-30": True,  # Saturday
            "2023-12-31": True,  # Sunday
        }
        self.assertEqual(work_days, expected_days)

    def test_flexible_employee_is_available_in_the_middle_of_a_day(self):
        self.env.user.company_id = self.company_A
        self.contractD.resource_calendar_id = False
        self.contractD.hours_per_week = 56
        self.contractD.hours_per_day = 8

        work_days = self.env["res.partner"]._get_unusual_days(
            [self.partnerD.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        expected_days = {
            "2023-12-25": False,  # Monday
            "2023-12-26": False,  # Tuesday
            "2023-12-27": False,  # Wednesday
            "2023-12-28": False,  # Thursday
            "2023-12-29": False,  # Friday
            "2023-12-30": False,  # Saturday
            "2023-12-31": False,  # Sunday
        }

        self.assertEqual(
            work_days,
            expected_days,
        )

    def test_flexible_employee_is_available_in_the_middle_of_day_after_contract_start(self):
        self.env.user.company_id = self.company_A
        self.contractD.resource_calendar_id = False
        self.contractD.hours_per_week = 56
        self.contractD.hours_per_day = 8
        self.contractD.contract_date_start = datetime(2023, 12, 28)

        work_days = self.env["res.partner"]._get_unusual_days(
            [self.partnerD.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        expected_days = {
            "2023-12-25": True,  # Monday
            "2023-12-26": True,  # Tuesday
            "2023-12-27": True,  # Wednesday
            "2023-12-28": False,  # Thursday
            "2023-12-29": False,  # Friday
            "2023-12-30": False,  # Saturday
            "2023-12-31": False,  # Sunday
        }

        self.assertEqual(
            work_days,
            expected_days,
        )

    def test_flexible_employee_is_always_available_until_contract_end(self):
        self.env.user.company_id = self.company_A
        self.contractD.resource_calendar_id = False
        self.contractD.hours_per_week = 56
        self.contractD.hours_per_day = 8
        self.contractD.contract_date_end = datetime(2023, 12, 28)

        work_days = self.env["res.partner"]._get_unusual_days(
            [self.partnerD.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        expected_days = {
            "2023-12-25": False,  # Monday
            "2023-12-26": False,  # Tuesday
            "2023-12-27": False,  # Wednesday
            "2023-12-28": False,  # Thursday
            "2023-12-29": True,  # Friday
            "2023-12-30": True,  # Saturday
            "2023-12-31": True,  # Sunday
        }

        self.assertEqual(
            work_days,
            expected_days,
        )

    def test_fully_flexible_employee_is_always_available(self):
        self.env.user.company_id = self.company_A
        self.contractD.resource_calendar_id = False
        self.contractD.hours_per_week = False
        self.contractD.hours_per_day = False

        work_days = self.env["res.partner"]._get_unusual_days(
            [self.partnerD.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        expected_days = {
            "2023-12-25": False,  # Monday
            "2023-12-26": False,  # Tuesday
            "2023-12-27": False,  # Wednesday
            "2023-12-28": False,  # Thursday
            "2023-12-29": False,  # Friday
            "2023-12-30": False,  # Saturday
            "2023-12-31": False,  # Sunday
        }

        self.assertEqual(
            work_days,
            expected_days,
        )

    def test_fully_flexible_employee_is_always_available_after_contract_start(self):
        self.env.user.company_id = self.company_A
        self.contractD.resource_calendar_id = False
        self.contractD.hours_per_week = False
        self.contractD.hours_per_day = False
        self.contractD.contract_date_start = datetime(2023, 12, 28)

        work_days = self.env["res.partner"]._get_unusual_days(
            [self.partnerD.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        expected_days = {
            "2023-12-25": True,  # Monday
            "2023-12-26": True,  # Tuesday
            "2023-12-27": True,  # Wednesday
            "2023-12-28": False,  # Thursday
            "2023-12-29": False,  # Friday
            "2023-12-30": False,  # Saturday
            "2023-12-31": False,  # Sunday
        }

        self.assertEqual(
            work_days,
            expected_days,
        )

    def test_fully_flexible_employee_is_always_available_until_contract_end(self):
        self.env.user.company_id = self.company_A
        self.contractD.resource_calendar_id = False
        self.contractD.hours_per_week = False
        self.contractD.hours_per_day = False
        self.contractD.contract_date_end = datetime(2023, 12, 28)

        work_days = self.env["res.partner"]._get_unusual_days(
            [self.partnerD.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        expected_days = {
            "2023-12-25": False,  # Monday
            "2023-12-26": False,  # Tuesday
            "2023-12-27": False,  # Wednesday
            "2023-12-28": False,  # Thursday
            "2023-12-29": True,  # Friday
            "2023-12-30": True,  # Saturday
            "2023-12-31": True,  # Sunday
        }

        self.assertEqual(
            work_days,
            expected_days,
        )
