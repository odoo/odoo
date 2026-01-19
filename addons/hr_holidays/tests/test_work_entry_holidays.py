# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

from odoo import SUPERUSER_ID
from odoo.exceptions import ValidationError
from odoo.tests.common import tagged
from odoo.fields import Date
from odoo.addons.hr_work_entry.tests.common import TestWorkEntryBase
from odoo.addons.hr_holidays.tests.common import TestHolidayContract
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged('work_entry')
@tagged('at_install', '-post_install')  # LEGACY at_install
class TestWorkeEntryHolidays(TestWorkEntryBase, TestHolidayContract):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tz = ZoneInfo(cls.richard_emp.tz)
        cls.start = datetime(2015, 11, 1, 1, 0, 0)
        cls.end = datetime(2015, 11, 30, 23, 59, 59)
        cls.resource_calendar_id = cls.env['resource.calendar'].create({'name': 'Zboub'})
        cls.richard_emp.create_version({
            'date_version': cls.start.date() - relativedelta(days=5),
            'contract_date_start': cls.start.date() - relativedelta(days=5),
            'contract_date_end': Date.to_date('2017-12-31'),
            'name': 'dodo',
            'resource_calendar_id': cls.resource_calendar_id.id,
            'wage': 1000,
        })

        cls.work_entry_type.requires_allocation = False

        cls.work_entry_type_remote = cls.env['hr.work.entry.type'].create({
            'name': 'Remote Work',
            'code': 'WORKTEST100',
            'count_as': 'working_time',
            'requires_allocation': False,
            'allow_request_on_top': True,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

        cls.half_day_work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Half-Day Leaves',
            'code': 'Half-Day Leaves',
            'count_as': 'absence',
            'request_unit': 'half_day',
            'requires_allocation': False,
        })

        cls.hours_work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Hours Leaves',
            'code': 'Hours Leaves',
            'count_as': 'absence',
            'request_unit': 'hour',
            'requires_allocation': False,
        })

        cls.external_company = cls.env['res.company'].create({'name': 'External Test company'})
        cls.external_user_employee = mail_new_test_user(cls.env, login='external', password='external', groups='base.group_user')
        cls.employee_external = cls.env['hr.employee'].create({
            'name': 'external Employee',
            'user_id': cls.external_user_employee.id,
            'company_id': cls.external_company.id,
            'date_version': cls.start.date() - relativedelta(days=5),
            'contract_date_start': cls.start.date() - relativedelta(days=5),
        })

    def test_time_week_leave_work_entry(self):
        # /!\ this is a week day => it exists an calendar attendance at this time
        self.work_entry_type.request_unit = 'hour'
        self.work_entry_type.unit_of_measure = 'hour'
        leave = self.env['hr.leave'].create({
            'name': '1leave',
            'employee_id': self.richard_emp.id,
            'work_entry_type_id': self.work_entry_type.id,
            'request_date_from': date(2015, 11, 2),
            'request_date_to': date(2015, 11, 2),
            'request_hour_from': 11,
            'request_hour_to': 17,
        })
        leave.action_approve()

        work_entries_vals = self.richard_emp.generate_work_entries(self.start.date(), self.end.date())
        leave_work_entries = [vals for vals in work_entries_vals if vals['work_entry_type_id'] == self.work_entry_type]
        sum_hours = sum(vals['duration'] for vals in leave_work_entries)

        self.assertEqual(sum_hours, 6.0, "It should equal the number of hours richard should have worked")

    def test_work_entries_generation_if_parent_leave_zero_hours(self):
        # Test case: The employee has a parental leave at 0 hours per week
        # The employee has a leave during that period

        calendar = self.env['resource.calendar'].create({
            'name': 'Parental 0h',
            'attendance_ids': False,
        })
        employee = self.env['hr.employee'].create({
            'name': 'My employee',
            'contract_date_start': self.start.date() - relativedelta(years=1),
            'contract_date_end': False,
            'resource_calendar_id': calendar.id,
            'wage': 1000,
        })

        work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Sick',
            'code': 'Sick',
            'request_unit': 'hour',
            'unit_of_measure': 'hour',
            'leave_validation_type': 'both',
            'requires_allocation': False,
            'count_as': 'absence',
        })

        leave = self.env['hr.leave'].create({
            'name': "Sick 1 that doesn't make sense, but it's the prod so YOLO",
            'employee_id': employee.id,
            'work_entry_type_id': work_entry_type.id,
            'request_date_from': date(2020, 9, 4),
            'request_date_to': date(2020, 9, 4),
        })

        # TODO I don't know what this test is supposed to test, but I feel that
        # in any case it should raise a Validation Error, as it's trying to
        # validate a leave in a period the employee is not supposed to work.
        with self.assertRaises(ValidationError):
            leave.action_approve()

        work_entries = employee.version_id.generate_work_entries(date(2020, 7, 1), date(2020, 9, 30))

        self.assertEqual(len(work_entries), 0)

    def test_work_entries_leave_if_leave_conflict_with_public_holiday(self):
        date_from = datetime(2023, 2, 1, 0, 0, 0)
        date_to = datetime(2023, 2, 28, 23, 59, 59)
        work_entry_type_holiday = self.env['hr.work.entry.type'].create({
            'name': 'Public Holiday',
            'count_as': 'absence',
            'code': 'LEAVETEST500'
        })
        self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'date_from': datetime(2023, 2, 6, 0, 0, 0),
            'date_to': datetime(2023, 2, 7, 23, 59, 59),
            'calendar_id': self.richard_emp.resource_calendar_id.id,
            'work_entry_type_id': work_entry_type_holiday.id,
        })
        leave = self.env['hr.leave'].create({
            'name': 'AL',
            'employee_id': self.richard_emp.id,
            'work_entry_type_id': self.work_entry_type.id,
            'request_date_from': date(2023, 2, 3),
            'request_date_to': date(2023, 2, 9),
        })
        leave.action_approve()

        work_entries_vals = self.richard_emp.generate_work_entries(date_from, date_to)
        leave_work_entries = [vals for vals in work_entries_vals if vals['work_entry_type_id'] == self.work_entry_type]
        self.assertEqual(leave_work_entries[0]['leave_ids'], leave, "Leave work entry should have leave_ids value")

        public_holiday_work_entry = [vals for vals in work_entries_vals if vals['work_entry_type_id'] == work_entry_type_holiday]
        self.assertFalse(public_holiday_work_entry[0].get('leave_ids'), "Public holiday work entry should not have leave_ids")

    def test_work_entries_overlap_work_leaves(self):
        remote = self.env['hr.leave'].create({
            'name': 'remote1',
            'employee_id': self.richard_emp.id,
            'work_entry_type_id': self.work_entry_type_remote.id,
            'request_date_from': date(2015, 11, 2),  # Monday
            'request_date_to': date(2015, 11, 6),
        })
        remote.action_approve()

        self.work_entry_type.request_unit = 'hour'
        self.work_entry_type.unit_of_measure = 'hour'
        self.work_entry_type.count_as = 'absence'
        leave = self.env['hr.leave'].create({
            'name': '1leave',
            'employee_id': self.richard_emp.id,
            'work_entry_type_id': self.work_entry_type.id,
            'request_date_from': date(2015, 11, 3),
            'request_date_to': date(2015, 11, 3),
            'request_hour_from': 11,
            'request_hour_to': 17,
        })
        leave.action_approve()

        work_entries_vals = self.richard_emp.generate_work_entries(self.start.date(), self.end.date())
        remote_work_entry = [vals for vals in work_entries_vals if vals['work_entry_type_id'] == self.work_entry_type_remote]
        leave_work_entry = [vals for vals in work_entries_vals if vals['work_entry_type_id'] == self.work_entry_type]
        self.assertEqual(len(remote_work_entry), 5, "There should be five remote work entries")
        self.assertEqual(len(leave_work_entry), 1, "There should be one leave work entry")
        sum_remote_hours = sum(vals['duration'] for vals in remote_work_entry)
        sum_leave_hours = sum(vals['duration'] for vals in leave_work_entry)
        self.assertEqual(sum_remote_hours, 35, "It should equal the number of hours richard worked in remote")  # 5 days * 8 hours - 5 hours for leave
        self.assertEqual(sum_leave_hours, 5.0, "It should equal the number of hours richard was on leave")

    def test_work_entries_overlap_half_day_leaves(self):
        """Test that half-day leaves correctly split work entries across multiple days.
        When a half-day leave spans two days (AM on day 1, AM on day 2), verify that:
        - The full-day work entry on day 1 is completely replaced by a leave entry
        - The full-day work entry on day 2 is split into a leave entry and attendance entry
        - All durations are correctly calculated (8h full day, 4h half day)
        """
        work_entries_vals = self.richard_emp.version_id._generate_work_entries(datetime(2025, 11, 1), datetime(2025, 11, 30))
        work_entries_vals = [
            vals for vals in work_entries_vals
            if vals['employee_id'] == self.richard_emp
            and vals['date'] >= date(2025, 11, 27)
            and vals['date'] <= date(2025, 11, 28)
        ]

        self.assertEqual(2, len(work_entries_vals))
        self.assertTrue(all(vals['duration'] == 8.0 for vals in work_entries_vals))
        attendance_work_entry_type_id = work_entries_vals[0]['work_entry_type_id']
        leave = self.env['hr.leave'].create({
            'name': 'Half-Day Leave',
            'employee_id': self.richard_emp.id,
            'request_date_from': date(2025, 11, 27),
            'request_date_from_period': 'am',
            'request_date_to': date(2025, 11, 28),
            'request_date_to_period': 'am',
            'work_entry_type_id': self.half_day_work_entry_type.id,
        })
        leave.action_approve()
        work_entries_vals = self.richard_emp.version_id._generate_work_entries(datetime(2025, 11, 1), datetime(2025, 11, 30))
        work_entries_vals = [
            vals for vals in work_entries_vals
            if vals['employee_id'] == self.richard_emp
            and vals['date'] >= date(2025, 11, 27)
            and vals['date'] <= date(2025, 11, 28)
        ]
        self.assertEqual(3, len(work_entries_vals))
        attendance_work_entry = [vals for vals in work_entries_vals if vals['work_entry_type_id'] == attendance_work_entry_type_id]
        self.assertEqual(1, len(attendance_work_entry))
        self.assertEqual(4.0, attendance_work_entry[0]['duration'])
        self.assertEqual(date(2025, 11, 28), attendance_work_entry[0]['date'], "The 27/11 work entry should be replaced")

        leave_work_entries = [vals for vals in work_entries_vals if vals['work_entry_type_id'] != attendance_work_entry_type_id]
        self.assertEqual(2, len(leave_work_entries))
        self.assertTrue(all(vals['work_entry_type_id'] in [self.work_entry_type_leave, self.half_day_work_entry_type] for vals in leave_work_entries))
        self.assertEqual(8.0, next(vals for vals in leave_work_entries if vals['date'] == date(2025, 11, 27))['duration'])
        self.assertEqual(4.0, next(vals for vals in leave_work_entries if vals['date'] == date(2025, 11, 28))['duration'])

    def test_work_entries_overlap_hours_leaves(self):
        """Test that hour-based leaves correctly split a single day's work entry.
        When an hours-based leave (e.g., 10:00-12:00) is taken within a workday, verify that:
        - The original 8-hour work entry is split into two entries
        - One attendance entry covers the non-leave hours (6h)
        - One leave entry covers the requested leave hours (2h)
        """
        work_entries_vals = self.richard_emp.version_id._generate_work_entries(datetime(2025, 11, 1), datetime(2025, 11, 30))
        work_entries_vals = [vals for vals in work_entries_vals if vals['employee_id'] == self.richard_emp and vals['date'] == date(2025, 11, 27)]
        self.assertEqual(1, len(work_entries_vals))
        self.assertEqual(8.0, work_entries_vals[0]['duration'])
        attendance_work_entry_type_id = work_entries_vals[0]['work_entry_type_id']
        leave = self.env['hr.leave'].create({
            'name': 'Hours Leave',
            'employee_id': self.richard_emp.id,
            'request_date_from': date(2025, 11, 27),
            'request_hour_from': 10.0,
            'request_date_to': date(2025, 11, 27),
            'request_hour_to': 12.0,
            'work_entry_type_id': self.hours_work_entry_type.id,
        })
        leave.action_approve()
        work_entries_vals = self.richard_emp.version_id._generate_work_entries(datetime(2025, 11, 1), datetime(2025, 11, 30))
        work_entries_vals = [vals for vals in work_entries_vals if vals['employee_id'] == self.richard_emp and vals['date'] == date(2025, 11, 27)]
        self.assertEqual(2, len(work_entries_vals))
        attendance_work_entry = [vals for vals in work_entries_vals if vals['work_entry_type_id'] == attendance_work_entry_type_id]
        self.assertEqual(1, len(attendance_work_entry))
        self.assertEqual(6.0, attendance_work_entry[0]['duration'])

        leave_work_entry = [vals for vals in work_entries_vals if vals['work_entry_type_id'] != attendance_work_entry_type_id]
        self.assertEqual(1, len(leave_work_entry))
        self.assertTrue(leave_work_entry[0]['work_entry_type_id'] == self.hours_work_entry_type)
        self.assertEqual(2.0, leave_work_entry[0]['duration'])

    def test_create_work_entry_for_flexible_employee_leave(self):
        work_entry_type_paid = self.env['hr.work.entry.type'].create([
            {
                'name': 'Paid leave',
                'code': 'PAID',
                'count_as': 'absence',
                'requires_allocation': False,
                'request_unit': 'hour',
                'unit_of_measure': 'hour',
            },
        ])

        self.jules_emp.write({
            'resource_calendar_id': False,
            'hours_per_week': 40,
            'hours_per_day': 8,
            'tz': self.jules_emp.tz
        })

        leave_paid = self.env['hr.leave'].create({
            'name': 'Paid leave',
            'employee_id': self.jules_emp.id,
            'work_entry_type_id': work_entry_type_paid.id,
            'request_date_from': datetime(2024, 9, 10),
            'request_date_to': datetime(2024, 9, 13),
        })
        leave_paid.with_user(SUPERUSER_ID)._action_validate()

        work_entries_vals = self.jules_emp.generate_work_entries(date(2024, 9, 10), date(2024, 9, 13))
        paid_leave_entry = [vals for vals in work_entries_vals if vals['work_entry_type_id'] == work_entry_type_paid]
        self.assertEqual(len(paid_leave_entry), 4, "Four work entries should be created for a flexible employee")
        self.assertEqual(sum(vals['duration'] for vals in work_entries_vals), 32, "The combined duration of the work entries for flexible employee should "
                                                                        "be number of days * hours per day")

    def test_refuse_approved_leave(self):
        start = datetime(2019, 10, 10, 6, 0)
        end = datetime(2019, 10, 10, 18, 0)
        # Setup contract generation state

        leave = self.create_leave(start, end)
        leave.action_approve()
        leave_work_entry_vals = self.richard_emp.version_id.generate_work_entries(start.date(), end.date())
        self.assertEqual(leave_work_entry_vals[:1][0]['leave_ids'], leave)
        leave.action_refuse()
        leave_work_entry_vals = self.richard_emp.version_id.generate_work_entries(start.date(), end.date())
        self.assertFalse(leave_work_entry_vals[:1][0].get('leave_ids'))

    def test_work_entry_generation_company_time_off(self):
        existing_leaves = self.env['hr.leave'].search([])
        existing_leaves.action_refuse()
        start = date(2022, 8, 1)
        end = date(2022, 8, 31)
        work_entries_vals = self.contract_cdi.generate_work_entries(start, end)
        work_entries_vals = [
            vals for vals in work_entries_vals
            if vals['employee_id'] == self.jules_emp
            and vals['date'] >= start
            and vals['date'] <= end
        ]
        self.assertTrue(len(list({vals['work_entry_type_id'] for vals in work_entries_vals})), 1)
        leave = self.env['hr.leave.generate.multi.wizard'].create({
            'name': 'Holiday!!!',
            'company_id': self.env.company.id,
            'work_entry_type_id': self.work_entry_type.id,
            'date_from': datetime(2022, 8, 8),
            'date_to': datetime(2022, 8, 8),
        })
        leave.action_generate_time_off()
        work_entries_vals = self.contract_cdi.generate_work_entries(start, end)
        work_entries_vals = [
            vals for vals in work_entries_vals
            if vals['employee_id'] == self.jules_emp
            and vals['date'] >= start
            and vals['date'] <= end
        ]
        self.assertTrue(len(list({vals['work_entry_type_id'] for vals in work_entries_vals})), 2)

    def test_split_leaves_by_entry_type(self):
        work_entry_type_paid, work_entry_type_unpaid = self.env['hr.work.entry.type'].create([
            {
                'name': 'Paid leave',
                'code': 'PAID',
                'count_as': 'absence',
                'requires_allocation': False,
                'request_unit': 'hour',
                'unit_of_measure': 'hour',
            },
            {
                'name': 'Unpaid leave',
                'code': 'UNPAID',
                'count_as': 'absence',
                'requires_allocation': False,
                'request_unit': 'hour',
                'unit_of_measure': 'hour',
            },
        ])

        leave_paid, leave_unpaid = self.env['hr.leave'].create([{
            'name': 'Paid leave',
            'employee_id': self.jules_emp.id,
            'work_entry_type_id': work_entry_type_paid.id,
            'request_date_from': datetime(2024, 9, 10),
            'request_date_to': datetime(2024, 9, 10),
            'request_hour_from': '8',
            'request_hour_to': '9',
        },
        {
            'name': 'Unpaid leave',
            'employee_id': self.jules_emp.id,
            'work_entry_type_id': work_entry_type_unpaid.id,
            'request_date_from': datetime(2024, 9, 10),
            'request_date_to': datetime(2024, 9, 10),
            'request_hour_from': '9',
            'request_hour_to': '10',
        }])

        (leave_paid | leave_unpaid).with_user(SUPERUSER_ID).action_approve()
        work_entries_vals = self.contract_cdi._generate_work_entries(datetime(2024, 9, 10, 0, 0, 0), datetime(2024, 9, 10, 23, 59, 59))
        paid_leave_entry = [vals for vals in work_entries_vals if vals['work_entry_type_id'] == work_entry_type_paid]
        unpaid_leave_entry = [vals for vals in work_entries_vals if vals['work_entry_type_id'] == work_entry_type_unpaid]

        self.assertEqual(len(work_entries_vals), 3, 'Leaves should have 1 entry per type')
        self.assertEqual(paid_leave_entry[0]['duration'], 1)
        self.assertEqual(unpaid_leave_entry[0]['duration'], 1)

    def test_work_data(self):
        leave = self.create_leave(datetime(2015, 11, 8, 8, 0), datetime(2015, 11, 10, 22, 0), name="Doctor Appointment", employee_id=self.jules_emp.id)
        leave.action_approve()

        work_entries_vals = self.jules_emp.version_ids.generate_work_entries(date(2015, 11, 10), date(2015, 11, 21))
        work_entries_vals = [vals for vals in work_entries_vals if vals['work_entry_type_id'] == self.env.ref('hr_work_entry.generic_work_entry_type_attendance')]
        sum_hours = sum(vals['duration'] for vals in work_entries_vals)
        self.assertEqual(sum_hours, 59, 'It should count 59 attendance hours')  # 24h first contract + 35h second contract

    def test_resource_leave_has_work_entry_type(self):
        leave = self.create_leave()

        resource_leave = leave._create_resource_leave()
        self.assertEqual(resource_leave.work_entry_type_id, self.work_entry_type, "it should have the corresponding work_entry type")

    def test_resource_leave_in_contract_calendar(self):
        other_calendar = self.env['resource.calendar'].create({'name': 'New calendar'})
        contract = self.richard_emp.version_id
        contract.resource_calendar_id = other_calendar
        leave = self.create_leave()

        resource_leave = leave._create_resource_leave()
        self.assertEqual(len(resource_leave), 1, "it should have created only one resource leave")
        self.assertEqual(resource_leave.work_entry_type_id, self.work_entry_type, "it should have the corresponding work_entry type")

    def test_multi_contract_holiday(self):
        # Leave during second contract
        leave = self.create_leave(datetime(2015, 11, 17), datetime(2015, 11, 20), name="Doctor Appointment", employee_id=self.jules_emp.id)
        leave.action_approve()
        start = datetime(2015, 11, 1, 0, 0, 0)
        end_generate = datetime(2015, 11, 30, 23, 59, 59)
        work_entries_vals = self.jules_emp.version_ids._generate_work_entries(start, end_generate)
        work_entries_vals = [vals for vals in work_entries_vals if vals['version_id'] == self.contract_cdi]

        work_entry_type_attendance_id = self.env.ref('hr_work_entry.generic_work_entry_type_attendance')
        work = [vals for vals in work_entries_vals if vals['work_entry_type_id'] == work_entry_type_attendance_id]
        leave = [vals for vals in work_entries_vals if vals['work_entry_type_id'] != work_entry_type_attendance_id]
        self.assertEqual(sum(vals['duration'] for vals in work), 49, "It should be 49 hours of work this month for this contract")
        self.assertEqual(sum(vals['duration'] for vals in leave), 28, "It should be 28 hours of leave this month for this contract")
