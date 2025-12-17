# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import Command
from odoo.tests import users, tagged
from odoo.addons.hr_calendar.tests.common import TestHrCalendarCommon, TestHrContractCalendarCommon
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged('work_hours')
@tagged('at_install', '-post_install')  # LEGACY at_install
class TestWorkingHours(TestHrCalendarCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_bxls = mail_new_test_user(
            cls.env,
            email='brussels@test.example.com',
            groups='base.group_user',
            name='Employee Brussels',
            notification_type='email',
            login='user_bxls',
        )
        if 'hr.version' in cls.env:
            cls.skipTest(cls,
                "hr_contract module is installed. To test these features you need to install test_hr_contract_calendar")

    def test_working_hours_2_emp_same_calendar(self):
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id]
        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerA.id, self.partnerD.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        self.assertEqual(work_hours, [
            {'daysOfWeek': [1], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [1], 'startTime': '13:00', 'endTime': '16:00'},
            {'daysOfWeek': [2], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [2], 'startTime': '13:00', 'endTime': '16:00'},
            {'daysOfWeek': [3], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [3], 'startTime': '13:00', 'endTime': '16:00'},
            {'daysOfWeek': [4], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [4], 'startTime': '13:00', 'endTime': '16:00'},
            {'daysOfWeek': [5], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [5], 'startTime': '13:00', 'endTime': '16:00'},
        ])

    def test_working_hours_2_emp_different_calendar(self):
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id]
        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerA.id, self.partnerB.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        # Nothing on monday due to partnerB's calendar : calendar_28h
        self.assertEqual(work_hours, [
            {'daysOfWeek': [2], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [2], 'startTime': '13:00', 'endTime': '16:00'},
            {'daysOfWeek': [3], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [3], 'startTime': '13:00', 'endTime': '16:00'},
            {'daysOfWeek': [4], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [4], 'startTime': '13:00', 'endTime': '16:00'},
            {'daysOfWeek': [5], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [5], 'startTime': '13:00', 'endTime': '16:00'},
        ])

    def test_working_hours_3_emp_different_calendar(self):
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id]
        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerA.id, self.partnerB.id, self.partnerC.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        # Nothing on monday due to partnerB's calendar : calendar_28h
        # Nothing before 15:00 due to partnerC's calendar : calendar_35h_night
        self.assertEqual(work_hours, [
            {'daysOfWeek': [2], 'startTime': '15:00', 'endTime': '16:00'},
            {'daysOfWeek': [3], 'startTime': '15:00', 'endTime': '16:00'},
            {'daysOfWeek': [4], 'startTime': '15:00', 'endTime': '16:00'},
            {'daysOfWeek': [5], 'startTime': '15:00', 'endTime': '16:00'}
        ])

    def test_working_hours_2_emp_same_calendar_hours_different_timezone(self):
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id]
        self.employeeD.resource_calendar_id = self.calendar_35h
        self.employeeD.tz = 'Europe/London'
        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerA.id, self.partnerD.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        # employeeD.tz = UTC +1
        self.assertEqual(work_hours, [
            {'daysOfWeek': [1], 'startTime': '09:00', 'endTime': '12:00'},
            {'daysOfWeek': [1], 'startTime': '14:00', 'endTime': '16:00'},
            {'daysOfWeek': [2], 'startTime': '09:00', 'endTime': '12:00'},
            {'daysOfWeek': [2], 'startTime': '14:00', 'endTime': '16:00'},
            {'daysOfWeek': [3], 'startTime': '09:00', 'endTime': '12:00'},
            {'daysOfWeek': [3], 'startTime': '14:00', 'endTime': '16:00'},
            {'daysOfWeek': [4], 'startTime': '09:00', 'endTime': '12:00'},
            {'daysOfWeek': [4], 'startTime': '14:00', 'endTime': '16:00'},
            {'daysOfWeek': [5], 'startTime': '09:00', 'endTime': '12:00'},
            {'daysOfWeek': [5], 'startTime': '14:00', 'endTime': '16:00'},
        ])

    def test_multi_companies_2_employees_1_selected_company(self):
        """
        INPUT:
        ======
        Employees                                   Companies
        employee A company A ---> 35h               [ ] A
        employee A company B ---> 28h               [X] B

        OUTPUT:
        =======
        The schedule will be the 28h's schedule
        """
        self.env.user.company_id = self.company_B
        self.env.user.company_ids = [self.company_B.id]

        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerA.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        self.assertEqual(work_hours, [
            {'daysOfWeek': [2], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [2], 'startTime': '13:00', 'endTime': '16:00'},
            {'daysOfWeek': [3], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [3], 'startTime': '13:00', 'endTime': '16:00'},
            {'daysOfWeek': [4], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [4], 'startTime': '13:00', 'endTime': '16:00'},
            {'daysOfWeek': [5], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [5], 'startTime': '13:00', 'endTime': '16:00'},
        ])

    def test_multi_companies_2_employees_2_selected_companies(self):
        """
        INPUT:
        ======
        Employees                                   Companies
        employee A company A ---> 35h               [X] A    <- main company
        employee A company B ---> 28h               [X] B

        OUTPUT:
        =======
        The schedule will be the 35h's schedule
        """
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id, self.company_B.id]
        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerA.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        self.assertEqual(work_hours, [
            {'daysOfWeek': [1], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [1], 'startTime': '13:00', 'endTime': '16:00'},
            {'daysOfWeek': [2], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [2], 'startTime': '13:00', 'endTime': '16:00'},
            {'daysOfWeek': [3], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [3], 'startTime': '13:00', 'endTime': '16:00'},
            {'daysOfWeek': [4], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [4], 'startTime': '13:00', 'endTime': '16:00'},
            {'daysOfWeek': [5], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [5], 'startTime': '13:00', 'endTime': '16:00'},
        ])

    def test_multi_companies_2_employees_2_selected_companies_union_between_schedules(self):
        """
        INPUT:
        ======
        Employees                                   Companies
        employee A company A ---> 35h               [X] A    <- main company
        employee A company B ---> 35h night         [X] B

        OUTPUT:
        =======
        The schedule will be the union between 35h's and 35h night's schedule
        """
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id, self.company_B.id]

        self.employeeA_company_B.resource_calendar_id = self.calendar_35h_night

        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerA.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        self.assertEqual(work_hours, [
            {'daysOfWeek': [1], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [1], 'startTime': '13:00', 'endTime': '22:00'},
            {'daysOfWeek': [2], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [2], 'startTime': '13:00', 'endTime': '22:00'},
            {'daysOfWeek': [3], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [3], 'startTime': '13:00', 'endTime': '22:00'},
            {'daysOfWeek': [4], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [4], 'startTime': '13:00', 'endTime': '22:00'},
            {'daysOfWeek': [5], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [5], 'startTime': '13:00', 'endTime': '21:00'},
            {'daysOfWeek': [0], 'startTime': '15:00', 'endTime': '16:00'},
        ])

    def test_multi_companies_2_employees_1_partner_1_selected_companies(self):
        """
        INPUT:
        ======
        Employees                                   Companies
        employee B1 company A ---> 28h               [X] A    <- main company
        employee B2 company A ---> 35h night         [ ] B

        OUTPUT:
        =======
        The schedule will be the union between 28h's and 35h night's schedule
        """
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id]

        self.env['hr.employee'].create({
            'name': "Partner B2 - Calendar 35h night",
            'tz': "Europe/Brussels",
            'resource_calendar_id': self.calendar_35h_night.id,
            'work_contact_id': self.partnerB.id,
            'company_id': self.company_A.id,
        })

        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerB.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        self.assertEqual(work_hours, [
            {'daysOfWeek': [1], 'startTime': '15:00', 'endTime': '22:00'},
            {'daysOfWeek': [2], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [2], 'startTime': '13:00', 'endTime': '22:00'},
            {'daysOfWeek': [3], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [3], 'startTime': '13:00', 'endTime': '22:00'},
            {'daysOfWeek': [4], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [4], 'startTime': '13:00', 'endTime': '22:00'},
            {'daysOfWeek': [5], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [5], 'startTime': '13:00', 'endTime': '21:00'},
            {'daysOfWeek': [0], 'startTime': '15:00', 'endTime': '16:00'},
        ])

    def test_work_hours_of_employee_without_time_zone(self):
        self.env.user.tz = False
        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerA.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        self.assertEqual(work_hours, [
            {'daysOfWeek': [1], 'startTime': '07:00', 'endTime': '11:00'},
            {'daysOfWeek': [1], 'startTime': '12:00', 'endTime': '15:00'},
            {'daysOfWeek': [2], 'startTime': '07:00', 'endTime': '11:00'},
            {'daysOfWeek': [2], 'startTime': '12:00', 'endTime': '15:00'},
            {'daysOfWeek': [3], 'startTime': '07:00', 'endTime': '11:00'},
            {'daysOfWeek': [3], 'startTime': '12:00', 'endTime': '15:00'},
            {'daysOfWeek': [4], 'startTime': '07:00', 'endTime': '11:00'},
            {'daysOfWeek': [4], 'startTime': '12:00', 'endTime': '15:00'},
            {'daysOfWeek': [5], 'startTime': '07:00', 'endTime': '11:00'},
            {'daysOfWeek': [5], 'startTime': '12:00', 'endTime': '15:00'},
        ])

    @users('user_bxls')
    def test_partner_on_leave_with_calendar_leave(self):
        """Check that resource leaves are correctly reflected in the unavailable_partner_ids field.
        Overlapping times between the leave time of an employee and the meeting should add the partner
        to the list of unavailable partners.
        """
        test_date = datetime(2022, 2, 14, 7, 0, 0)
        self.employeeA.user_id = self.user_bxls
        self.env['calendar.event'].search([('user_id', '=', self.user_bxls.id)]).unlink()
        self.env['resource.calendar.leaves'].sudo().search([('calendar_id', '=', self.user_bxls.resource_calendar_id.id)]).unlink()

        meeting = self.env['calendar.event'].with_context(company_id=self.company_A.id).create([
            {
                'start': test_date,
                'stop': test_date + timedelta(hours=3),
                'name': "Event",
                'attendee_ids': [(0, 0, {'partner_id': self.user_bxls.partner_id.id})],
            },
        ])
        self.assertFalse(meeting.unavailable_partner_ids)

        self.env['resource.calendar.leaves'].sudo().create({
            'calendar_id': self.user_bxls.resource_calendar_id.id,
            'date_from': test_date,
            'date_to': test_date + timedelta(days=1),
            'name': 'Casual Leave'
        })
        meeting.invalidate_recordset()
        self.assertEqual(meeting.unavailable_partner_ids, self.user_bxls.partner_id)


@tagged('work_hours')
@tagged('at_install', '-post_install')  # LEGACY at_install
class TestWorkingHoursWithVersion(TestHrContractCalendarCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_working_hours_2_emp_same_calendar(self):
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id]

        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerA.id, self.partnerD.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat()
        )
        self.assertEqual(work_hours, [
            {'daysOfWeek': [1], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [1], 'startTime': '13:00', 'endTime': '16:00'},
            {'daysOfWeek': [2], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [2], 'startTime': '13:00', 'endTime': '16:00'},
            {'daysOfWeek': [3], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [3], 'startTime': '13:00', 'endTime': '16:00'},
            {'daysOfWeek': [4], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [4], 'startTime': '13:00', 'endTime': '16:00'},
            {'daysOfWeek': [5], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [5], 'startTime': '13:00', 'endTime': '16:00'},
        ])

    def test_working_hours_2_emp_contract_start(self):
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id]

        self.contractB.contract_date_start = datetime(2023, 12, 28)
        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerA.id, self.partnerB.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat()
        )
        # Nothing on monday, tuesday and wednesday due to contractB. (start : thursday 2023/12/28)
        self.assertEqual(work_hours, [
            {'daysOfWeek': [4], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [4], 'startTime': '13:00', 'endTime': '16:00'},
            {'daysOfWeek': [5], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [5], 'startTime': '13:00', 'endTime': '16:00'},
        ])

    def test_working_hours_2_emp_contract_stop(self):
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id]

        self.contractB.date_end = datetime(2023, 12, 28)
        self.contractB.contract_date_end = datetime(2023, 12, 28)
        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerA.id, self.partnerB.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat()
        )
        # Nothing on monday due to calendarB.
        # Nothing on Friday due to contractB (stop : thursday 2023/12/28)
        self.assertEqual(work_hours, [
            {'daysOfWeek': [2], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [2], 'startTime': '13:00', 'endTime': '16:00'},
            {'daysOfWeek': [3], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [3], 'startTime': '13:00', 'endTime': '16:00'},
            {'daysOfWeek': [4], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [4], 'startTime': '13:00', 'endTime': '16:00'},
        ])

    def test_working_hours_3_emp_different_calendar(self):
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id]

        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerA.id, self.partnerB.id, self.partnerC.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat()
        )
        # Nothing on monday due to partnerB's calendar : calendar_2
        # Nothing before 15:00 due to partnerC's calendar : calendar_3
        # Nothing on tuesday and wednesday due to contractC. (start : thursday 2023/12/28)
        self.assertEqual(work_hours, [
            {'daysOfWeek': [4], 'startTime': '15:00', 'endTime': '16:00'},
            {'daysOfWeek': [5], 'startTime': '15:00', 'endTime': '16:00'},
        ])

    def test_working_hours_2_emp_same_calendar_different_timezone(self):
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id]
        self.contractD.resource_calendar_id = self.calendar_35h
        self.contractD.tz = 'Europe/London'
        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerA.id, self.partnerD.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat()
        )
        # contractD.tz = UTC +1
        self.assertEqual(work_hours, [
            {'daysOfWeek': [1], 'startTime': '09:00', 'endTime': '12:00'},
            {'daysOfWeek': [1], 'startTime': '14:00', 'endTime': '16:00'},
            {'daysOfWeek': [2], 'startTime': '09:00', 'endTime': '12:00'},
            {'daysOfWeek': [2], 'startTime': '14:00', 'endTime': '16:00'},
            {'daysOfWeek': [3], 'startTime': '09:00', 'endTime': '12:00'},
            {'daysOfWeek': [3], 'startTime': '14:00', 'endTime': '16:00'},
            {'daysOfWeek': [4], 'startTime': '09:00', 'endTime': '12:00'},
            {'daysOfWeek': [4], 'startTime': '14:00', 'endTime': '16:00'},
            {'daysOfWeek': [5], 'startTime': '09:00', 'endTime': '12:00'},
            {'daysOfWeek': [5], 'startTime': '14:00', 'endTime': '16:00'}
        ])

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
        work_hours = self.env["res.partner"].get_working_hours_for_all_attendees(
            self.partnerD.ids,
            datetime(2023, 12, 29).isoformat(),  # Friday
            datetime(2024, 1, 1).isoformat(),  # Monday
        )
        # sunday_morning_calendar.tz = GMT+5, viewers_calendar.tz = GMT +1, difference = 4 hours "back in time"
        expected_hours = [
            {"daysOfWeek": [6], "startTime": "20:00", "endTime": "23:59"},  # Saturday
            {"daysOfWeek": [0], "startTime": "00:00", "endTime": "04:00"},  # Sunday
        ]
        self.assertEqual(work_hours, expected_hours)

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

        work_hours = self.env["res.partner"].get_working_hours_for_all_attendees(
            self.partnerD.ids,
            datetime(2023, 12, 30).isoformat(),  # Saturday
            datetime(2023, 12, 30).isoformat(),  # Saturday
        )
        # sunday_morning_calendar.tz = GMT-8, viewers_calendar.tz = GMT +1, difference = 9 hours "forwards in time"
        expected_hours = [
            {"daysOfWeek": [6], "startTime": "20:00", "endTime": "23:59"},  # Saturday
        ]
        self.assertEqual(work_hours, expected_hours)

        work_hours = self.env["res.partner"].get_working_hours_for_all_attendees(
            self.partnerD.ids,
            datetime(2023, 12, 31).isoformat(),  # Sunday
            datetime(2023, 12, 31).isoformat(),  # Sunday
        )
        # sunday_morning_calendar.tz = GMT-8, viewers_calendar.tz = GMT +1, difference = 9 hours "forwards in time"
        expected_hours = [
            {"daysOfWeek": [0], "startTime": "00:00", "endTime": "04:00"},  # Sunday
        ]
        self.assertEqual(work_hours, expected_hours)

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
        work_hours = self.env["res.partner"].get_working_hours_for_all_attendees(
            self.partnerD.ids,
            datetime(2023, 12, 29).isoformat(),  # Friday
            datetime(2024, 1, 1).isoformat(),  # Monday
        )
        # sunday_morning_calendar.tz = GMT-8, viewers_calendar.tz = GMT +1, difference = 9 hours "forwards in time"
        expected_hours = [
            {"daysOfWeek": [0], "startTime": "17:00", "endTime": "23:59"},  # Sunday
            {"daysOfWeek": [1], "startTime": "00:00", "endTime": "02:00"},  # Monday
        ]
        self.assertEqual(work_hours, expected_hours)

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

        work_hours = self.env["res.partner"].get_working_hours_for_all_attendees(
            self.partnerD.ids,
            datetime(2023, 12, 31).isoformat(),  # Sunday
            datetime(2023, 12, 31).isoformat(),  # Sunday
        )
        expected_hours = [
            {"daysOfWeek": [0], "startTime": "17:00", "endTime": "23:59"},  # Sunday
        ]
        self.assertEqual(work_hours, expected_hours)

        work_hours = self.env["res.partner"].get_working_hours_for_all_attendees(
            self.partnerD.ids,
            datetime(2024, 1, 1).isoformat(),  # Monday
            datetime(2024, 1, 1).isoformat(),  # Monday
        )
        expected_hours = [
            {"daysOfWeek": [1], "startTime": "00:00", "endTime": "02:00"},  # Monday
        ]
        self.assertEqual(work_hours, expected_hours)

    def test_working_hours_with_employee_without_contract(self):
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id]

        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerA.id, self.partnerE.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat()
        )
        # Employee E doesn't have a contract
        self.assertEqual(work_hours, [{'daysOfWeek': [7], 'startTime': '00:00', 'endTime': '00:00'}])

    def test_working_hours_one_employee_with_two_contracts(self):
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id]

        # Contract from november
        self.env['hr.version'].create({
            'date_version': datetime(2023, 11, 1),
            'contract_date_start': datetime(2023, 11, 1),
            'contract_date_end': datetime(2023, 11, 30),
            'name': 'Contract november',
            'resource_calendar_id': self.calendar_35h_night.id,
            'wage': 5000.0,
            'employee_id': self.employeeA.id,
        })
        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerA.id],
            datetime(2023, 11, 27).isoformat(),
            datetime(2023, 12, 3).isoformat()
        )
        self.assertEqual(work_hours, [
            {'daysOfWeek': [1], 'startTime': '15:00', 'endTime': '22:00'},
            {'daysOfWeek': [2], 'startTime': '15:00', 'endTime': '22:00'},
            {'daysOfWeek': [3], 'startTime': '15:00', 'endTime': '22:00'},
            {'daysOfWeek': [4], 'startTime': '15:00', 'endTime': '22:00'},
            {'daysOfWeek': [5], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [5], 'startTime': '13:00', 'endTime': '16:00'},
        ])

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

        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerB.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat()
        )
        self.assertEqual(work_hours, [
            {'daysOfWeek': [1], 'startTime': '15:00', 'endTime': '22:00'},
            {'daysOfWeek': [2], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [2], 'startTime': '13:00', 'endTime': '22:00'},
            {'daysOfWeek': [3], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [3], 'startTime': '13:00', 'endTime': '22:00'},
            {'daysOfWeek': [4], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [4], 'startTime': '13:00', 'endTime': '22:00'},
            {'daysOfWeek': [5], 'startTime': '08:00', 'endTime': '12:00'},
            {'daysOfWeek': [5], 'startTime': '13:00', 'endTime': '22:00'},
        ])

    def test_flexible_employee_is_available_in_the_middle_of_a_day(self):
        self.env.user.company_id = self.company_A
        self.contractD.resource_calendar_id = False
        self.contractD.hours_per_week = 56
        self.contractD.hours_per_day = 8

        work_hours = self.env["res.partner"].get_working_hours_for_all_attendees(
            [self.partnerD.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        expected_hours = [
            {"daysOfWeek": [1], "startTime": "08:00", "endTime": "16:00"},  # Monday
            {"daysOfWeek": [2], "startTime": "08:00", "endTime": "16:00"},  # Tuesday
            {"daysOfWeek": [3], "startTime": "08:00", "endTime": "16:00"},  # Wednesday
            {"daysOfWeek": [4], "startTime": "08:00", "endTime": "16:00"},  # Thursday
            {"daysOfWeek": [5], "startTime": "08:00", "endTime": "16:00"},  # Friday
            {"daysOfWeek": [6], "startTime": "08:00", "endTime": "16:00"},  # Saturday
            {"daysOfWeek": [0], "startTime": "08:00", "endTime": "16:00"},  # Sunday
        ]

        self.assertEqual(
            work_hours,
            expected_hours,
        )

    def test_flexible_employee_is_available_in_the_middle_of_day_after_contract_start(self):
        self.env.user.company_id = self.company_A
        self.contractD.resource_calendar_id = False
        self.contractD.hours_per_week = 56
        self.contractD.hours_per_day = 8
        self.contractD.contract_date_start = datetime(2023, 12, 28)

        work_hours = self.env["res.partner"].get_working_hours_for_all_attendees(
            [self.partnerD.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        expected_hours = [
            {"daysOfWeek": [4], "startTime": "08:00", "endTime": "16:00"},  # Thursday
            {"daysOfWeek": [5], "startTime": "08:00", "endTime": "16:00"},  # Friday
            {"daysOfWeek": [6], "startTime": "08:00", "endTime": "16:00"},  # Saturday
            {"daysOfWeek": [0], "startTime": "08:00", "endTime": "16:00"},  # Sunday
        ]

        self.assertEqual(
            work_hours,
            expected_hours,
        )

    def test_flexible_employee_is_always_available_until_contract_end(self):
        self.env.user.company_id = self.company_A
        self.contractD.resource_calendar_id = False
        self.contractD.hours_per_week = 56
        self.contractD.hours_per_day = 8
        self.contractD.contract_date_end = datetime(2023, 12, 28)

        work_hours = self.env["res.partner"].get_working_hours_for_all_attendees(
            [self.partnerD.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        expected_hours = [
            {"daysOfWeek": [1], "startTime": "08:00", "endTime": "16:00"},  # Monday
            {"daysOfWeek": [2], "startTime": "08:00", "endTime": "16:00"},  # Tuesday
            {"daysOfWeek": [3], "startTime": "08:00", "endTime": "16:00"},  # Wednesday
            {"daysOfWeek": [4], "startTime": "08:00", "endTime": "16:00"},  # Thursday
        ]

        self.assertEqual(
            work_hours,
            expected_hours,
        )

    def test_fully_flexible_employee_is_always_available(self):
        self.env.user.company_id = self.company_A
        self.contractD.resource_calendar_id = False
        self.contractD.hours_per_week = False
        self.contractD.hours_per_day = False

        work_hours = self.env["res.partner"].get_working_hours_for_all_attendees(
            [self.partnerD.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        expected_hours = [
            {"daysOfWeek": [1], "startTime": "00:00", "endTime": "23:59"},  # Monday
            {"daysOfWeek": [2], "startTime": "00:00", "endTime": "23:59"},  # Tuesday
            {"daysOfWeek": [3], "startTime": "00:00", "endTime": "23:59"},  # Wednesday
            {"daysOfWeek": [4], "startTime": "00:00", "endTime": "23:59"},  # Thursday
            {"daysOfWeek": [5], "startTime": "00:00", "endTime": "23:59"},  # Friday
            {"daysOfWeek": [6], "startTime": "00:00", "endTime": "23:59"},  # Saturday
            {"daysOfWeek": [0], "startTime": "00:00", "endTime": "23:59"},  # Sunday
        ]

        self.assertEqual(
            work_hours,
            expected_hours,
        )

    def test_fully_flexible_employee_is_always_available_after_contract_start(self):
        self.env.user.company_id = self.company_A
        self.contractD.resource_calendar_id = False
        self.contractD.hours_per_week = False
        self.contractD.hours_per_day = False
        self.contractD.contract_date_start = datetime(2023, 12, 28)

        work_hours = self.env["res.partner"].get_working_hours_for_all_attendees(
            [self.partnerD.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        expected_hours = [
            {"daysOfWeek": [4], "startTime": "00:00", "endTime": "23:59"},  # Thursday
            {"daysOfWeek": [5], "startTime": "00:00", "endTime": "23:59"},  # Friday
            {"daysOfWeek": [6], "startTime": "00:00", "endTime": "23:59"},  # Saturday
            {"daysOfWeek": [0], "startTime": "00:00", "endTime": "23:59"},  # Sunday
        ]

        self.assertEqual(
            work_hours,
            expected_hours,
        )

    def test_fully_flexible_employee_is_always_available_until_contract_end(self):
        self.env.user.company_id = self.company_A
        self.contractD.resource_calendar_id = False
        self.contractD.hours_per_week = False
        self.contractD.hours_per_day = False
        self.contractD.contract_date_end = datetime(2023, 12, 28)

        work_hours = self.env["res.partner"].get_working_hours_for_all_attendees(
            [self.partnerD.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        expected_hours = [
            {"daysOfWeek": [1], "startTime": "00:00", "endTime": "23:59"},  # Monday
            {"daysOfWeek": [2], "startTime": "00:00", "endTime": "23:59"},  # Tuesday
            {"daysOfWeek": [3], "startTime": "00:00", "endTime": "23:59"},  # Wednesday
            {"daysOfWeek": [4], "startTime": "00:00", "endTime": "23:59"},  # Thursday
        ]

        self.assertEqual(
            work_hours,
            expected_hours,
        )

    def test_event_with_flexible_and_default_calendar_employees(self):
        """
        If an employee is marked as Fully Flexible, their default calendar should be `env.company.resource_calendar_id`.
        If one employee has no calendar assigned (indicating full flexibility) and another uses the default calendar,
        they should still be grouped together in the same work intervals.
        """
        expected_partners = self.partnerF | self.partnerG
        event = self.env['calendar.event'].with_context(company_id=self.company_A.id).create([
            {
                'start': datetime(2024, 7, 12, 8, 30, 0),
                'stop': datetime(2024, 7, 12, 9, 30, 0),
                'name': "Event X",
                'partner_ids': [
                    Command.link(self.partnerF.id),
                    Command.link(self.partnerG.id),
                ]
            },
        ])

        # Need to read unavailable_partner_ids to force being computed and trigger _get_schedule
        self.assertEqual(event.unavailable_partner_ids.ids, [], "All partners must be available!")
        self.assertEqual(expected_partners.ids, event.partner_ids.ids, "All partners must be invited!")
