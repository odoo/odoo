# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pytz import timezone

from datetime import datetime, date

from odoo.addons.hr_contract.tests.common import TestContractCommon


class TestAttendances(TestContractCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.resource_calendar_id.tz = "Europe/Brussels"

        resource_calendar_half_time = cls.env['resource.calendar'].create([{
            'name': "Test Calendar: Half Time",
            'company_id': cls.env.company.id,
            'tz': "Europe/Brussels",
            'two_weeks_calendar': False,
            'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                'name': "Attendance",
                'dayofweek': dayofweek,
                'hour_from': hour_from,
                'hour_to': hour_to,
                'day_period': day_period,
            }) for dayofweek, hour_from, hour_to, day_period in [
                ("0", 8.0, 12.0, "morning"),
                ("0", 13.0, 16.6, "afternoon"),
                ("1", 8.0, 12.0, "morning"),
                ("1", 13.0, 16.6, "afternoon"),
                ("2", 8.0, 11.8, "morning"),
            ]],
        }])

        contract_now = cls.env['hr.contract'].create({
            'name': 'Current Contract',
            'employee_id': cls.employee.id,
            'state': "open",
            'wage': 1,
            'date_start': date(2024, 6, 1),
            'date_end': date(2024, 6, 30),
        })

        cls.env['hr.contract'].create({
            'name': 'Next Contract',
            'employee_id': cls.employee.id,
            'resource_calendar_id': resource_calendar_half_time.id,
            'state': "open",
            'wage': 1,
            'date_start': date(2024, 7, 1),
            'date_end': False,
        })

        cls.employee.resource_calendar_id = contract_now.resource_calendar_id

    def test_incoming_overlapping_contract(self):
        tz = timezone("Europe/Brussels")
        check_in_tz = datetime.combine(datetime(2024, 6, 1), datetime.min.time()).astimezone(tz)
        check_out_tz = datetime.combine(datetime(2024, 6, 30), datetime.max.time()).astimezone(tz)
        intervals = self.employee._get_expected_attendances(check_in_tz, check_out_tz)
        self.assertEqual(len(intervals), 40)

        check_in_tz = datetime.combine(datetime(2024, 7, 1), datetime.min.time()).astimezone(tz)
        check_out_tz = datetime.combine(datetime(2024, 7, 31), datetime.max.time()).astimezone(tz)
        intervals = self.employee._get_expected_attendances(check_in_tz, check_out_tz)
        self.assertEqual(len(intervals), 25)
