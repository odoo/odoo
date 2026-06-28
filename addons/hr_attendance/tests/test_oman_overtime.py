# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, date
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('hr_attendance_overtime')
class TestOmanOvertimeRegression(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.oman_company = cls.env['res.company'].create({
            'name': 'Oman Test Branch',
            'country_id': cls.env.ref('base.om').id,
        })

        cls.oman_ruleset = cls.env.ref('hr_attendance.l10n_om_overtime_ruleset')

        cls.oman_employee = cls.env['hr.employee'].with_company(cls.oman_company).create({
            'name': 'Ahmed Oman Test Employee',
            'company_id': cls.oman_company.id,
            'tz': 'UTC',
            'ruleset_id': cls.oman_ruleset.id,
            'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1),
        })

    def test_oman_standard_hours_no_accidental_overtime(self):
        attendance = self.env['hr.attendance'].with_company(self.oman_company).create({
            'employee_id': self.oman_employee.id,
            'check_in': datetime(2026, 6, 9, 9, 0, 0),
            'check_out': datetime(2026, 6, 9, 17, 0, 0),
        })

        attendance._update_overtime()

        self.assertAlmostEqual(
            attendance.overtime_hours, 0.0, places=2,
            msg="Regression Failure: Standard daytime work hours are still generating accidental overtime."
        )
