# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pytz import timezone

from datetime import datetime, date

from odoo.addons.hr.tests.common import TestHrCommon


class TestAttendances(TestHrCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.resource_calendar_id.tz = "Europe/Brussels"

        contract_now = cls.employee.create_version({
            'wage': 1,
            'contract_date_start': date(2024, 6, 1),
            'date_version': date(2024, 6, 1),
        })

        resource_calendar_half_time = cls.env['resource.calendar'].create([{
            'name': "Test Calendar: Half Time",
            'company_id': cls.env.company.id,
            'tz': "Europe/Brussels",
            'attendance_ids': [(5, 0, 0)] + [(0, 0, {
                'dayofweek': dayofweek,
                'hour_from': hour_from,
                'hour_to': hour_to,
                'break_hours': break_hours,
            }) for dayofweek, hour_from, hour_to, break_hours in [
                ("0", 8.0, 16.6, 1),
                ("1", 8.0, 16.6, 1),
                ("2", 8.0, 11.8, 0),
            ]],
        }])

        cls.employee.create_version({
            'resource_calendar_id': resource_calendar_half_time.id,
            'contract_date_start': date(2024, 6, 1),
            'wage': 1,
            'date_version': date(2024, 7, 1),
        })

        cls.employee.resource_calendar_id = contract_now.resource_calendar_id

    def test_incoming_overlapping_contract(self):
        tz = timezone("Europe/Brussels")
        check_in_tz = datetime.combine(datetime(2024, 6, 1), datetime.min.time()).astimezone(tz)
        check_out_tz = datetime.combine(datetime(2024, 6, 30), datetime.max.time()).astimezone(tz)
        intervals = self.employee._employee_attendance_intervals(check_in_tz, check_out_tz, lunch=False)
        self.assertEqual(len(intervals), 40)

        check_in_tz = datetime.combine(datetime(2024, 7, 1), datetime.min.time()).astimezone(tz)
        check_out_tz = datetime.combine(datetime(2024, 7, 31), datetime.max.time()).astimezone(tz)
        intervals = self.employee._employee_attendance_intervals(check_in_tz, check_out_tz, lunch=False)
        self.assertEqual(len(intervals), 25)
