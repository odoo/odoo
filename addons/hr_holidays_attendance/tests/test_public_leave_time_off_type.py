# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from freezegun import freeze_time

from odoo import Command
from odoo.tests import Form
from odoo.tests.common import tagged
from odoo.addons.hr_attendance.tests.test_hr_attendance_overtime import TestHrAttendanceOvertime


@tagged('hr_attendance_overtime')
class TestPublicLeaveTimeOffType(TestHrAttendanceOvertime):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_overtime_with_public_leave_timing_type(self):
        """
        Validate that a public leave timing type is correctly applied.
        Comapny 1 has a public holiday, while Company 2 does not.
        Employee from Company 2 should not get overtime for working that day.
        Also Employee from Company 1 should not get overtime for working on a weekend.
        """

        with freeze_time("2025-11-11 12:00:00"):
            self.env.user.tz = 'UTC'  # to avoid to shift the public holidays hours
            company_be = self.env['res.company'].create({'name': 'Odoo BE'})
            company_de = self.env['res.company'].create({'name': 'Odoo DE'})

            with Form(self.env['resource.calendar.leaves'].with_company(company_be)) as holiday_form:
                holiday_form.name = 'Armistice Day'
                holiday_form.date_from = datetime(2025, 11, 11, 0, 0)
                holiday_form.save()

            ruleset_be = self.env['hr.attendance.overtime.ruleset'].with_company(company_be).create({
                'name': 'Ruleset schedule timing',
                'rule_ids': [Command.create({
                    'name': 'Rule schedule timing',
                    'base_off': 'timing',
                    'timing_type': 'public_leave',
                    'timing_start': 0,
                    'timing_stop': 24,
                })],
            })
            ruleset_de = self.env['hr.attendance.overtime.ruleset'].with_company(company_de).create({
                'name': 'Ruleset schedule timing',
                'rule_ids': [Command.create({
                    'name': 'Rule schedule timing',
                    'base_off': 'timing',
                    'timing_type': 'public_leave',
                    'timing_start': 0,
                    'timing_stop': 24,
                })],
            })

            employee_be = self.env['hr.employee'].with_company(company_be).create({
                'name': 'Hans Belgian',
                'ruleset_id': ruleset_be.id,
            })
            employee_de = self.env['hr.employee'].with_company(company_de).create({
                'name': 'Henry German',
                'ruleset_id': ruleset_de.id,
            })

            attendance_company_be = self.env['hr.attendance'].create({
                'employee_id': employee_be.id,
                'check_in': datetime(2025, 11, 11, 8, 0),
                'check_out': datetime(2025, 11, 11, 17, 0),
            })
            attendance_company_de = self.env['hr.attendance'].create({
                'employee_id': employee_de.id,
                'check_in': datetime(2025, 11, 11, 8, 0),
                'check_out': datetime(2025, 11, 11, 17, 0),
            })
            attendance_saturday_be = self.env['hr.attendance'].create({
                'employee_id': employee_be.id,
                'check_in': datetime(2025, 11, 15, 8, 0),  # Saturday
                'check_out': datetime(2025, 11, 15, 17, 0),
            })

            self.assertAlmostEqual(attendance_company_be.overtime_hours, 9, 2,
                                   "Employee from Company 1 should have overtime for working on a public holiday.")
            self.assertAlmostEqual(attendance_company_de.overtime_hours, 0, 2,
                                   "Employee from Company 2 should not have overtime for working on a non-holiday day.")
            self.assertAlmostEqual(attendance_saturday_be.overtime_hours, 0, 2,
                                   "Shouldn't have overtime for working on a public holiday.")
