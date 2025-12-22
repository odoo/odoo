# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from odoo.addons.hr_calendar.tests.common import TestHrCalendarCommon

from odoo.tests import tagged


@tagged('work_hours')
class TestWorkingHours(TestHrCalendarCommon):
    """ Test global leaves for a whole company, conflict resolutions """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if 'hr.contract' in cls.env:
            cls.skipTest(cls,
                "hr_contract module is installed. To test these features you need to install hr_holidays_contract"
            )

        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Unpaid Time Off',
            'requires_allocation': 'no',
            'leave_validation_type': 'no_validation',
        })

    def test_multi_companies_2_employees_2_selected_companies_holidays(self):
        """
        INPUT:
        ======
        Employees                                   Companies
        employee A company A ---> 35h               [X] A    <- main company
        employee A company B ---> 28h               [X] B
        employee A company A take a day off for monday and tuesday.
        OUTPUT:
        =======
        The schedule will be : off on monday, following 28h schedule on tuesday and the union for the rest of the week.
        """
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id, self.company_B.id]

        self.env['hr.leave'].create({
            'name': 'holiday from monday to tuesday',
            'employee_id': self.employeeA.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': datetime(2023, 12, 25),
            'request_date_to': datetime(2023, 12, 26, 23, 59, 59),
        })

        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerA.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat()
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

    def test_multi_companies_2_employees_2_selected_companies_company_holidays(self):
        """
        INPUT:
        ======
        Employees                                   Companies
        employee A company A ---> 35h               [X] A    <- main company
        employee A company B ---> 28h               [X] B
        Company A give a day off for everyone on monday and tuesday.
        OUTPUT:
        =======
        The schedule will be : off on monday, following 28h schedule on tuesday and the union for the rest of the week.
        """
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id, self.company_B.id]

        company_leave = self.env['hr.leave.generate.multi.wizard'].create({
            'name': 'holiday from monday to tuesday',
            'allocation_mode': 'company',
            'company_id': self.company_A.id,
            'holiday_status_id': self.leave_type.id,
            'date_from': date(2023, 12, 25),
            'date_to': date(2023, 12, 26),
        })
        company_leave.action_generate_time_off()

        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerA.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat()
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

    def test_multi_companies_2_employees_2_selected_companies_global_holidays(self):
        """
        INPUT:
        ======
        Employees                                   Companies
        employee A company A ---> 35h               [X] A    <- main company
        employee A company B ---> 28h               [X] B
        Global leave for calendar 35h on monday and tuesday.
        OUTPUT:
        =======
        The schedule will be : off on monday, following 28h schedule on tuesday and the union for the rest of the week.
        """
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id, self.company_B.id]

        self.env['resource.calendar.leaves'].create({
            'name': 'Global Time Off',
            'date_from': datetime(2023, 12, 25),
            'date_to': datetime(2023, 12, 26, 23, 59, 59),
            'calendar_id': self.calendar_35h.id,
        })

        work_hours = self.env['res.partner'].get_working_hours_for_all_attendees(
            [self.partnerA.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat()
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
