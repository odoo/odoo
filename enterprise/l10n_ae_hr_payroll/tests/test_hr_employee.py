# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests import common, tagged


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestHrEmployee(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_worked_years(self):
        employee_1 = self.env['hr.employee'].create({
            'name': 'Test Employee 1',
        })

        self.env['hr.contract'].create({
            'name': 'Test Contract 1',
            'employee_id': employee_1.id,
            'wage': 15_000.0,
            'state': 'open',
            'date_start': date(2023, 2, 15),
        })

        departure_notice_1 = self.env['hr.departure.wizard'].create({
            'employee_id': employee_1.id,
            'departure_date': date(2025, 2, 14),
            'departure_description': 'foo',
        })
        departure_notice_1.with_context(toggle_active=True).action_register_departure()

        self.assertAlmostEqual(employee_1._l10n_ae_get_worked_years(), 2, 2, "This employee has worked for 2 years")
