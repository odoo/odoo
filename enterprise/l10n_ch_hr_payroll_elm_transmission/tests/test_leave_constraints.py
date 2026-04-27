# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestSwissdecCommon
from odoo.tests.common import tagged
from datetime import date
from odoo.exceptions import ValidationError


@tagged("post_install_l10n", "post_install", "-at_install", "swissdec_payroll")
class TestLeaveConstraints(TestSwissdecCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.employee_monica = (
            cls.env["hr.employee"]
            .with_context(tracking_disable=True)
            .create(
                {
                    "name": "Monica Herz",
                    "resource_calendar_id": cls.env.ref("resource.resource_calendar_std").id,
                    "company_id": cls.muster_ag_company.id,
                    "country_id": cls.env.ref("base.ch").id,
                },
            )
        )
        cls.interruption_work_leave_type = cls.env.ref(
            "l10n_ch_hr_payroll_elm_transmission.l10n_ch_swissdec_interruption_of_work_lt",
            raise_if_not_found=False,
        )

    def test_work_interruption_leave_incorrect_start_or_end(self):
        with self.assertRaises(ValidationError):
            self.env["hr.leave"].create(
                {
                    "name": "Interruption of work Time Off Apr",
                    "employee_id": self.employee_monica.id,
                    "holiday_status_id": self.interruption_work_leave_type.id,
                    "request_date_from": date(2023, 4, 1),
                    "request_date_to": date(2023, 4, 24),
                }
            )
        with self.assertRaises(ValidationError):
            self.env["hr.leave"].create(
                {
                    "name": "Interruption of work Time Off May",
                    "employee_id": self.employee_monica.id,
                    "holiday_status_id": self.interruption_work_leave_type.id,
                    "request_date_from": date(2023, 5, 5),
                    "request_date_to": date(2023, 5, 31),
                }
            )
        self.env["hr.leave"].create(
            {
                "name": "Interruption of work Time Off Apr",
                "employee_id": self.employee_monica.id,
                "holiday_status_id": self.interruption_work_leave_type.id,
                "request_date_from": date(2023, 4, 1),
                "request_date_to": date(2023, 4, 30),
            }
        )

    def test_work_interruption_leave_non_standard_working_schedule(self):
        resource_calendar_20_hours_per_week = self.env['resource.calendar'].create({
                'name': "Test Calendar : 40 Hours/Week",
                'hours_per_day': 4.0,
                'tz': "Europe/Zurich",
                'two_weeks_calendar': False,
                'hours_per_week': 20.0,
                'full_time_required_hours': 20.0,
                'attendance_ids': [
                    (0, 0, {'name': "Attendance", 'dayofweek': "0", 'hour_from': 0.0, 'hour_to': 4.0, 'day_period': "morning"}),
                    (0, 0, {'name': "Attendance", 'dayofweek': "1", 'hour_from': 0.0, 'hour_to': 4.0, 'day_period': "morning"}),
                    (0, 0, {'name': "Attendance", 'dayofweek': "2", 'hour_from': 0.0, 'hour_to': 4.0, 'day_period': "morning"}),
                    (0, 0, {'name': "Attendance", 'dayofweek': "3", 'hour_from': 0.0, 'hour_to': 4.0, 'day_period': "morning"}),
                    (0, 0, {'name': "Attendance", 'dayofweek': "4", 'hour_from': 0.0, 'hour_to': 4.0, 'day_period': "morning"}),
                ],
            })
        self.employee_monica.resource_calendar_id = resource_calendar_20_hours_per_week
        self.env["hr.leave"].create(
            {
                "name": "Interruption of work Time Off Apr",
                "employee_id": self.employee_monica.id,
                "holiday_status_id": self.interruption_work_leave_type.id,
                "request_date_from": date(2023, 4, 1),
                "request_date_to": date(2023, 4, 30),
            }
        )
