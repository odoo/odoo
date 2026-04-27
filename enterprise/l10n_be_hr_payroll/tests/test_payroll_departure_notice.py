# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests import tagged
from .common import TestPayrollCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPayrollDepartureNotice(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.pfi_employee = cls.env['hr.employee'].create({
            'name': 'PFI Employee',
        })

        cls.pfi_employee_contract = cls.env['hr.contract'].create({
            'name': "PFI employee's contract",
            'employee_id': cls.pfi_employee.id,
            'date_start': date(2025, 1, 1),
            'contract_type_id': cls.env.ref('l10n_be_hr_payroll.l10n_be_contract_type_pfi').id,
            'wage': 5000,
            'state': 'open'
        })

    def test_departure_notice_only_PFI(self):
        """
        When the employee only has one PFI contract, there is no notice period. The start and end date of the notice
        period should then be the departure date.
        """
        wizard = self.env['hr.payslip.employee.depature.notice'].with_context(allowed_company_ids=self.belgian_company.ids, active_id=self.pfi_employee.id).create({
            'departure_date': date(2025, 2, 1),
            'leaving_type_id': self.env.ref('hr.departure_fired').id,
            'departure_description': 'PFI fired'
        })
        self.assertEqual(wizard.oldest_contract_id, self.env['hr.contract'])
        self.assertEqual(wizard.first_contract, False)
        self.assertEqual(wizard.start_notice_period, date(2025, 2, 1))
        self.assertEqual(wizard.end_notice_period, date(2025, 2, 1))
        self.assertEqual(wizard.notice_duration_week_after_2014, 0)

    def test_departure_notice_first_PFI(self):
        """
        When the employee only has multiple contracts, including a PFI contract, the PFI contract should not be taken
        into account to compute the seniority.
        """
        self.pfi_employee_contract.date_end = date(2025, 1, 31)
        second_contract_cdi = self.env['hr.contract'].create({
            'name': "CDI employee's contract",
            'employee_id': self.pfi_employee.id,
            'date_start': date(2025, 2, 1),
            'contract_type_id': self.env.ref('l10n_be_hr_payroll.l10n_be_contract_type_cdi').id,
            'wage': 5000,
            'state': 'open'
        })
        wizard = self.env['hr.payslip.employee.depature.notice'].with_context(allowed_company_ids=self.belgian_company.ids, active_id=self.pfi_employee.id).create({
            'departure_date': date(2025, 3, 1),
            'leaving_type_id': self.env.ref('hr.departure_fired').id,
            'departure_description': 'CDI fired'
        })
        self.assertEqual(wizard.oldest_contract_id, second_contract_cdi)
        self.assertEqual(wizard.first_contract, date(2025, 2, 1))
