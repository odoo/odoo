# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestHourlyRate(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        us = cls.env.ref('base.us')
        cls.structure = cls.env.ref('l10n_us_hr_payroll.hr_payroll_structure_us_employee_salary')
        cls.overtime_type = cls.env.ref('hr_work_entry.overtime_work_entry_type')
        cls.work100_type = cls.env.ref('hr_work_entry.work_entry_type_attendance')

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'country_id': us.id,
            'company_id': cls.env.company.id,
        })
        cls.contract = cls.env['hr.contract'].create({
            'name': 'Test Contract',
            'employee_id': cls.employee.id,
            'structure_type_id': cls.env.ref('l10n_us_hr_payroll.structure_type_employee_us').id,
            'wage_type': 'hourly',
            'hourly_wage': 26,
            'wage': 0,
            'date_start': date(2026, 1, 1),
            'state': 'open',
        })
        cls.payslip = cls.env['hr.payslip'].create({
            'name': 'Test Payslip',
            'employee_id': cls.employee.id,
            'contract_id': cls.contract.id,
            'struct_id': cls.structure.id,
            'date_from': date(2026, 1, 1),
            'date_to': date(2026, 1, 31),
        })

    def test_overtime_hourly_rate(self):
        worked_day = self.env['hr.payslip.worked_days'].create({
            'payslip_id': self.payslip.id,
            'work_entry_type_id': self.overtime_type.id,
            'number_of_days': 1,
            'number_of_hours': 0.00166667,  # 6 seconds
        })
        self.assertAlmostEqual(worked_day._l10n_us_get_hourly_rate(), 39.0)

    def test_regular_hourly_rate(self):
        worked_day = self.env['hr.payslip.worked_days'].create({
            'payslip_id': self.payslip.id,
            'work_entry_type_id': self.work100_type.id,
            'number_of_days': 1,
            'number_of_hours': 8,
        })
        self.assertAlmostEqual(worked_day._l10n_us_get_hourly_rate(), 26.0)
