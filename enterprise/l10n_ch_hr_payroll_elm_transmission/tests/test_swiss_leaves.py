from odoo.tests.common import tagged
from odoo.exceptions import ValidationError
from .common import TestSwissdecCommon
from datetime import date
from unittest.mock import patch


@tagged('post_install_l10n', 'post_install', '-at_install', 'swissdec_payroll')
class TestSwissLeaves(TestSwissdecCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_ch = cls.env['res.company'].create({
            'name': 'Swiss Test Company',
            'country_id': cls.env.ref('base.ch').id,
        })
        cls.employee_ch = cls.env['hr.employee'].create({
            'name': 'Swiss Test Employee',
            'company_id': cls.company_ch.id,
            'lang': 'en_US',
        })
        cls.contract_ch = cls.env['hr.contract'].create({
            'name': 'Swiss Test Contract',
            'employee_id': cls.employee_ch.id,
            'company_id': cls.company_ch.id,
            'date_start': date(2024, 1, 1),
            'date_end': date(2026, 12, 31),
            'wage': 5000,
        })
        cls.non_payroll_impacting_leave_type = cls.env['hr.leave.type'].create({
            'name': 'Swiss Leave Type 1',
            'company_id': cls.company_ch.id,
            'requires_allocation': 'no',
            'l10n_ch_swissdec_payroll_impact': False,
        })
        cls.payroll_impacting_leave_type = cls.env['hr.leave.type'].create({
            'name': 'Swiss Leave Type 2',
            'company_id': cls.company_ch.id,
            'requires_allocation': 'no',
            'l10n_ch_swissdec_payroll_impact': True,
        })
        cls.patcher = patch.object(
            cls.env['hr.payslip'].__class__,
            '_get_payroll_impacting_swissdec',
            return_value=cls.env['hr.leave.type'].browse([cls.payroll_impacting_leave_type.id])
        )
        cls.patcher.start()
        cls.addClassCleanup(cls.patcher.stop)

        cls._l10n_ch_generate_swissdec_demo_payslip(cls.contract_ch, date(2025, 1, 1), date(2025, 1, 31), cls.company_ch.id)

    def _create_leave(self, employee, leave_type, date_from, date_to, continued_pay_percentage=1, disability_percentage=1):
        return self.env['hr.leave'].create({
            'name': f"Leave {leave_type.name}",
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': date_from,
            'request_date_to': date_to,
            'l10n_ch_continued_pay_percentage': continued_pay_percentage,
            'l10n_ch_disability_percentage': disability_percentage,
        })

    def test_ch_leave_creation(self):
        self._create_leave(
            self.employee_ch,
            self.non_payroll_impacting_leave_type,
            date(2025, 1, 1),
            date(2025, 1, 5),
        )
        self._create_leave(
            self.employee_ch,
            self.non_payroll_impacting_leave_type,
            date(2025, 1, 6),
            date(2025, 1, 12),
            continued_pay_percentage=0.8
        )
        self._create_leave(
            self.employee_ch,
            self.payroll_impacting_leave_type,
            date(2025, 1, 15),
            date(2025, 1, 20),
        )
        self._create_leave(
            self.employee_ch,
            self.payroll_impacting_leave_type,
            date(2025, 2, 10),
            date(2025, 2, 20),
            continued_pay_percentage=0.8,
            disability_percentage=0.9,
        )

        with self.assertRaises(ValidationError):
            self._create_leave(
                self.employee_ch,
                self.payroll_impacting_leave_type,
                date(2025, 1, 25),
                date(2025, 1, 31),
                continued_pay_percentage=0.5,
            )
        with self.assertRaises(ValidationError):
            self._create_leave(
                self.employee_ch,
                self.payroll_impacting_leave_type,
                date(2025, 1, 25),
                date(2025, 1, 31),
                disability_percentage=0.5,
            )
