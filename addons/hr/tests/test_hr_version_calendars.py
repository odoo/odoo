from datetime import date
from pytz import utc
from odoo.tests.common import TransactionCase
from odoo.fields import Datetime


class TestHrVersionCalendars(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'Test Company',
            'country_id': cls.env.ref('base.us').id,
        })
        cls.env.user.company_id = cls.company
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Youssef Ahmed',
            'date_version': '2025-01-01',
            'date_start': '2025-01-01',
        })

        cls.calendar_1 = cls.env['resource.calendar'].create([{
            'name': "Standard 40 hours/week",
            'company_id': cls.env.company.id,
            'tz': "UTC",
            'two_weeks_calendar': False,
            'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                'name': "Attendance",
                'dayofweek': dayofweek,
                'hour_from': hour_from,
                'hour_to': hour_to,
                'day_period': day_period,
            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 8.0, 12.0, "morning"),
                ("0", 13.0, 17.0, "afternoon"),
                ("1", 8.0, 12.0, "morning"),
                ("1", 13.0, 17.0, "afternoon"),
                ("2", 8.0, 12.0, "morning"),
                ("2", 13.0, 17.0, "afternoon"),
                ("3", 8.0, 12.0, "morning"),
                ("3", 13.0, 17.0, "afternoon"),
                ("4", 8.0, 12.0, "morning"),
                ("4", 13.0, 17.0, "afternoon"),
            ]],
        }])

        cls.calendar_2 = cls.env['resource.calendar'].create([{
            'name': "Standard 20 hours/week",
            'company_id': cls.env.company.id,
            'tz': "UTC",
            'two_weeks_calendar': False,
            'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                'name': "Attendance",
                'dayofweek': dayofweek,
                'hour_from': hour_from,
                'hour_to': hour_to,
                'day_period': day_period,
            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 8.0, 12.0, "morning"),
                ("1", 8.0, 12.0, "morning"),
                ("2", 8.0, 12.0, "morning"),
                ("3", 8.0, 12.0, "morning"),
                ("4", 8.0, 12.0, "morning"),

            ]],
        }])

        cls.start = Datetime.from_string('2025-01-01 00:00:00').replace(tzinfo=utc)
        cls.stop = Datetime.from_string('2025-01-31 23:59:59').replace(tzinfo=utc)

    def test_01_two_versions_same_contract_same_calendar(self):
        v1 = self.employee.version_id
        v1.name = "Version 1"
        v1.resource_calendar_id = self.calendar_1.id

        v2 = self.employee.create_version({
            'name': "Version 2",
            'date_version': '2025-01-16',
            'resource_calendar_id': self.calendar_1.id,
        })

        contract_versions = v1 | v2
        contract_versions.contract_date_start = date(2025, 1, 1)

        periods = self.employee._get_calendar_periods(self.start, self.stop)
        employee_periods = periods[self.employee]
        self.assertEqual(len(employee_periods), 2)

        self.assertEqual(employee_periods[0][0].date(), date(2025, 1, 1))
        self.assertEqual(employee_periods[0][1].date(), date(2025, 1, 16))
        self.assertEqual(employee_periods[0][2].id, self.calendar_1.id)

        self.assertEqual(employee_periods[1][0].date(), date(2025, 1, 16))
        self.assertEqual(employee_periods[1][1].date(), date(2025, 1, 31))
        self.assertEqual(employee_periods[1][2].id, self.calendar_1.id)

    def test_02_two_versions_same_contract_different_calendars(self):
        v1 = self.employee.version_id
        v1.name = "Version 1"
        v1.resource_calendar_id = self.calendar_1.id

        v2 = self.employee.create_version({
            'name': "Version 2",
            'date_version': '2025-01-16',
            'resource_calendar_id': self.calendar_2.id,
        })

        contract_versions = v1 | v2
        contract_versions.contract_date_start = date(2025, 1, 1)

        periods = self.employee._get_calendar_periods(self.start, self.stop)
        employee_periods = periods[self.employee]
        self.assertEqual(len(employee_periods), 2)

        self.assertEqual(employee_periods[0][0].date(), date(2025, 1, 1))
        self.assertEqual(employee_periods[0][1].date(), date(2025, 1, 16))
        self.assertEqual(employee_periods[0][2].id, self.calendar_1.id)

        self.assertEqual(employee_periods[1][0].date(), date(2025, 1, 16))
        self.assertEqual(employee_periods[1][1].date(), date(2025, 1, 31))
        self.assertEqual(employee_periods[1][2].id, self.calendar_2.id)

    def test_03_two_versions_different_contracts_different_calendars(self):
        v1 = self.employee.version_id
        v1.name = "Version 1"
        v1.resource_calendar_id = self.calendar_1.id

        v1.contract_date_start = date(2025, 1, 1)
        v1.contract_date_end = date(2025, 1, 15)

        v2 = self.employee.create_version({
            'name': "Version 2",
            'date_version': '2025-01-16',
            'resource_calendar_id': self.calendar_2.id,
        })

        v2.contract_date_start = date(2025, 1, 16)
        v2.contract_date_end = date(2025, 1, 31)

        periods = self.employee._get_calendar_periods(self.start, self.stop)
        employee_periods = periods[self.employee]

        self.assertEqual(len(employee_periods), 2)

        self.assertEqual(employee_periods[0][0].date(), date(2025, 1, 1))
        self.assertEqual(employee_periods[0][1].date(), date(2025, 1, 16))
        self.assertEqual(employee_periods[0][2].id, self.calendar_1.id)

        self.assertEqual(employee_periods[1][0].date(), date(2025, 1, 16))
        self.assertEqual(employee_periods[1][1].date(), date(2025, 1, 31))
        self.assertEqual(employee_periods[1][2].id, self.calendar_2.id)

    def test_04_two_versions_without_contract_different_calendars(self):
        v1 = self.employee.version_id
        v1.name = "Version 1"
        v1.resource_calendar_id = self.calendar_1.id

        self.employee.create_version({
            'name': "Version 2",
            'date_version': '2025-01-16',
            'resource_calendar_id': self.calendar_2.id,
        })

        self.employee.contract_date_start = ''
        periods = self.employee._get_calendar_periods(self.start, self.stop)

        self.assertEqual(len(periods[self.employee]), 0)
