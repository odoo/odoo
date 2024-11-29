# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from datetime import datetime
from odoo.addons.test_hr_contract_calendar.tests.common import TestHrContractCalendarCommon


@tagged('work_hours')
class TestWorkingHours(TestHrContractCalendarCommon):
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

        self.contractB.date_start = datetime(2023, 12, 28)
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
        self.env['hr.contract'].create({
            'date_start': datetime(2023, 11, 1),
            'date_end': datetime(2023, 11, 30),
            'name': 'Contract november',
            'resource_calendar_id': self.calendar_35h_night.id,
            'wage': 5000.0,
            'employee_id': self.employeeA.id,
            'state': 'close',
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

        # to check if the resource calendar on the contract takes priority
        self.employeeB.resource_calendar_id = self.calendar_35h.id

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
