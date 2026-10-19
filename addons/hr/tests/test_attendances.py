# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from zoneinfo import ZoneInfo

from odoo.tests import tagged

from odoo.addons.hr.tests.common import TestHrCommon


class TestAttendances(TestHrCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.tz = "Europe/Brussels"

        contract_now = cls.employee.create_version({
            'wage': 1,
            'contract_date_start': date(2024, 6, 1),
            'date_version': date(2024, 6, 1),
        })

        resource_calendar_half_time = cls.env['resource.calendar'].create([{
            'name': "Test Calendar: Half Time",
            'company_id': cls.env.company.id,
            'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                'dayofweek': dayofweek,
                'hour_from': hour_from,
                'hour_to': hour_to,
            }) for dayofweek, hour_from, hour_to in [
                ("0", 8.0, 12.0),
                ("0", 13.0, 16.6),
                ("1", 8.0, 12.0),
                ("1", 13.0, 16.6),
                ("2", 8.0, 11.8),
            ]],
        }])

        cls.employee.create_version({
            'resource_calendar_id': resource_calendar_half_time.id,
            'contract_date_start': date(2024, 6, 1),
            'contract_date_end': date(2024, 7, 31),
            'wage': 1,
            'date_version': date(2024, 7, 1),
        })

        cls.employee.create_version({
            'contract_date_start': date(2024, 8, 1),
            'wage': 1,
            'date_version': date(2024, 9, 1),
        })

        cls.employee.resource_calendar_id = contract_now.resource_calendar_id

    def test_incoming_overlapping_contract(self):
        tz = ZoneInfo("Europe/Brussels")
        check_in_tz = datetime.combine(datetime(2024, 6, 1), datetime.min.time()).astimezone(tz)
        check_out_tz = datetime.combine(datetime(2024, 6, 30), datetime.max.time()).astimezone(tz)
        intervals = self.employee._get_expected_attendances(check_in_tz, check_out_tz)
        self.assertEqual(len(intervals), 40)

        check_in_tz = datetime.combine(datetime(2024, 7, 1), datetime.min.time()).astimezone(tz)
        check_out_tz = datetime.combine(datetime(2024, 7, 31), datetime.max.time()).astimezone(tz)
        intervals = self.employee._get_expected_attendances(check_in_tz, check_out_tz)
        self.assertEqual(len(intervals), 25)

        check_in_tz = datetime.combine(datetime(2024, 8, 1), datetime.min.time()).astimezone(tz)
        check_out_tz = datetime.combine(datetime(2024, 8, 31), datetime.max.time()).astimezone(tz)
        intervals = self.employee._get_expected_attendances(check_in_tz, check_out_tz)
        self.assertEqual(len(intervals), 20)
