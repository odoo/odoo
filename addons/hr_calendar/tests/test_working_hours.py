# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta
from freezegun import freeze_time

from odoo import Command
from odoo.tests import users, tagged
from odoo.addons.hr_calendar.tests.common import TestHrCalendarCommon, TestHrContractCalendarCommon
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged('work_hours')
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
        # TODO RETH get rid of these tests since they can never run
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
        calendar_35h_london_tz = self.calendar_35h.copy()
        calendar_35h_london_tz.tz = 'Europe/London'
        self.employeeD.resource_calendar_id = calendar_35h_london_tz
        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerA.id, self.partnerD.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        # calendar_35h_london_tz.tz = UTC, calendar_35h.tz = UTC +1
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
class TestWorkingHoursWithVersion(TestHrContractCalendarCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_bxls = mail_new_test_user(
            cls.env,
            company_id=cls.company_A.id,
            email='brussels@test.example.com',
            groups='base.group_user',
            name='User Brussels',
            notification_type='email',
            login='user_bxls',
        )

    def test_event_unavailable_partner_ids_without_contract(self):
        """Check that new employees with no ongoing contract are available
        to attend meetings during their assigned calendar hours.
        """
        # create employee and its first version before contract start
        # otherwise it will mess with availability
        with freeze_time(datetime(2024, 6, 1)):
            self.user_bxls.action_create_employee()
        employee = self.user_bxls.employee_ids
        company_calendar = self.env.company.resource_calendar_id
        employee_partner = self.user_bxls.partner_id
        self.assertEqual(len(employee), 1)
        self.assertEqual(len(employee.version_ids), 1)
        self.assertEqual(employee.version_ids.contract_date_start, False)
        self.assertTrue(employee.resource_calendar_id)
        self.assertEqual(employee.resource_calendar_id, company_calendar)
        cases = [
            # no contract scheduled to start -> available based on employee calendar
            (self.env['res.partner'], datetime(2024, 7, 12, 8, 30), datetime(2024, 7, 12, 9, 30), company_calendar, False, False),
            # no contract scheduled to start -> not available based on employee calendar
            (employee_partner, datetime(2024, 7, 12, 5, 30), datetime(2024, 7, 12, 9, 30), company_calendar, False, False),
            # no contract and no calendar -> always available, considered flexible schedule
            (self.env['res.partner'], datetime(2024, 7, 11, 1), datetime(2024, 7, 14, 16, 30), False, False, False),
            # contract starts same day -> available based on contract calendar
            (self.env['res.partner'], datetime(2024, 7, 12, 8, 30), datetime(2024, 7, 12, 9, 30), company_calendar, date(2024, 7, 12), False),
            # contract starts in a few days -> unavailable despite valid for employee calendar
            (employee_partner, datetime(2024, 7, 12, 8, 30), datetime(2024, 7, 12, 9, 30), company_calendar, date(2024, 7, 14), False),
            # contract finished -> unavailable despite valid for employee calendar
            (employee_partner, datetime(2024, 7, 12, 8, 30), datetime(2024, 7, 12, 9, 30), company_calendar, date(2024, 7, 10), date(2024, 7, 11)),
        ]
        for expected_unavailable_partners, start, stop, employee_calendar, version_contract_start, version_contract_end in cases:
            employee.version_ids.write({
                'contract_date_start': version_contract_start,
                'contract_date_end': version_contract_end,
            })
            employee.resource_calendar_id = employee_calendar
            employee.version_ids.resource_calendar_id = employee_calendar
            with self.subTest(
                start=start, stop=stop, employee_calendar=employee_calendar,
                contract_start=version_contract_start, contract_end=version_contract_end
            ):
                event = self.env['calendar.event'].new({
                    'start': start,
                    'stop': stop,
                    'name': 'Event X',
                    'partner_ids': employee_partner,
                })
                self.assertEqual(event.unavailable_partner_ids.ids, expected_unavailable_partners.ids)

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

        calendar_35h_london_tz = self.calendar_35h.copy()
        calendar_35h_london_tz.tz = 'Europe/London'
        self.contractD.resource_calendar_id = calendar_35h_london_tz
        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerA.id, self.partnerD.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat()
        )
        # calendar_35h_london_tz.tz = UTC, calendar_35h.tz = UTC +1
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
