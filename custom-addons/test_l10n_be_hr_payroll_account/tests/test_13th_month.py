# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date

from odoo.tests import tagged
from odoo.addons.test_l10n_be_hr_payroll_account.tests.test_payslip import TestPayslipBase


@tagged('thirteen_month')
class Test13thMonth(TestPayslipBase):

    def setUp(self):
        super(Test13thMonth, self).setUp()
        self.structure = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_thirteen_month')
        contract = self.employee.contract_id
        self.payslip = self.create_payslip(contract, self.structure, datetime(2019, 12, 1), datetime(2019, 12, 31))

    def _adjust_payslip(self, contract):
        self.payslip.contract_id = contract
        self.payslip.struct_id = self.structure
        self.payslip.date_from = datetime(2019, 12, 1)
        self.payslip.date_to = datetime(2019, 12, 31)

    def test_end_of_year_bonus(self):
        self._adjust_payslip(self.create_contract(date(2015, 1, 1)))

        work_entries = self.employee.contract_ids.generate_work_entries(date(2018, 12, 31), date(2019, 12, 31))
        work_entries.action_validate()

        self.payslip.compute_sheet()

        self.check_payslip('end of year bonus', self.payslip, {
            'BASIC': 2500.0,
            'SALARY': 2500.0,
            'ONSS': -326.75,
            'GROSS': 2173.25,
            'P.P': -943.41,
            'NET': 1229.84,
        })

    def test_13th_month_paid_amount_full_year(self):
        contract = self.create_contract(date(2015, 1, 24))
        work_entries = self.employee.contract_ids.generate_work_entries(date(2018, 12, 31), date(2019, 12, 31))
        work_entries.action_validate()
        self._adjust_payslip(contract)
        self.assertEqual(self.payslip._get_paid_amount(), 2500, 'It should be the full December wage')

    def test_13th_month_paid_amount_after_july(self):
        contract = self.create_contract(date(2019, 7, 4))
        work_entries = self.employee.contract_ids.generate_work_entries(date(2018, 12, 31), date(2019, 12, 31))
        work_entries.action_validate()
        self._adjust_payslip(contract)
        self.assertEqual(self.payslip._get_paid_amount(), 0, 'This is not a full month')

    def test_13th_month_paid_amount_first_july(self):
        contract = self.create_contract(date(2019, 7, 1))
        work_entries = self.employee.contract_ids.generate_work_entries(date(2018, 12, 31), date(2019, 12, 31))
        work_entries.action_validate()
        self._adjust_payslip(contract)
        self.assertEqual(self.payslip._get_paid_amount(), 1250, 'It should be count 6 months')

    def test_13th_month_paid_amount_month_start(self):
        contract = self.create_contract(date(2019, 6, 3))  # 3rd June 2019 is a Monday => June should count
        work_entries = self.employee.contract_ids.generate_work_entries(date(2018, 12, 31), date(2019, 12, 31))
        work_entries.action_validate()
        self._adjust_payslip(contract)
        self.assertAlmostEqual(self.payslip._get_paid_amount(), contract.wage * 7 / 12, msg='It should count 7/12 months')

    def test_13th_month_paid_amount_month_middle(self):
        contract = self.create_contract(date(2019, 6, 10))  # in the middle of June => June should not count
        work_entries = self.employee.contract_ids.generate_work_entries(date(2018, 12, 31), date(2019, 12, 31))
        work_entries.action_validate()
        self._adjust_payslip(contract)
        self.assertAlmostEqual(self.payslip._get_paid_amount(), contract.wage * 6 / 12, msg='It should count 6/12 months')

    def test_13th_month_paid_amount_multiple_contracts(self):
        self.create_contract(date(2019, 1, 1), date(2019, 3, 31))
        contract = self.create_contract(date(2019, 10, 1))
        work_entries = self.employee.contract_ids.generate_work_entries(date(2018, 12, 31), date(2019, 12, 31))
        work_entries.action_validate()
        self._adjust_payslip(contract)
        self.assertAlmostEqual(self.payslip._get_paid_amount(), contract.wage * 6 / 12, msg='It should count 6/12 months')

    def test_13th_month_paid_amount_multiple_contracts_gap(self):
        self.create_contract(date(2019, 1, 1), date(2019, 3, 31))
        contract = self.create_contract(date(2019, 11, 1))
        work_entries = self.employee.contract_ids.generate_work_entries(date(2018, 12, 31), date(2019, 12, 31))
        work_entries.action_validate()
        self._adjust_payslip(contract)
        self.assertAlmostEqual(self.payslip._get_paid_amount(), 0, msg='It should count O months as the total is less than 6 months')

    def test_13th_month_paid_amount_multiple_contracts_middle(self):
        self.create_contract(date(2019, 1, 1), date(2019, 3, 13))  # middle of the week
        contract = self.create_contract(date(2019, 3, 14))  # starts the following day
        work_entries = self.employee.contract_ids.generate_work_entries(date(2018, 12, 31), date(2019, 12, 31))
        work_entries.action_validate()
        self._adjust_payslip(contract)
        self.assertAlmostEqual(self.payslip._get_paid_amount(), contract.wage, msg='It should count all months')

    def test_13th_month_paid_amount_multiple_contracts_weekend(self):
        self.create_contract(date(2019, 1, 1), date(2019, 3, 15))  # ends a Friday
        contract = self.create_contract(date(2019, 3, 18))  # starts the following Monday
        work_entries = self.employee.contract_ids.generate_work_entries(date(2018, 12, 31), date(2019, 12, 31))
        work_entries.action_validate()
        self._adjust_payslip(contract)
        self.assertAlmostEqual(self.payslip._get_paid_amount(), contract.wage, msg='It should count all months')

    def test_13th_month_paid_amount_multiple_contracts_next_week(self):
        self.create_contract(date(2019, 1, 1), date(2019, 3, 15))  # ends a Friday
        contract = self.create_contract(date(2019, 3, 19))  # starts the following Tuesday
        work_entries = self.employee.contract_ids.generate_work_entries(date(2018, 12, 31), date(2019, 12, 31))
        work_entries.action_validate()
        self._adjust_payslip(contract)
        self.assertAlmostEqual(self.payslip._get_paid_amount(), contract.wage * 11 / 12, msg='It should count 11/12 months')

    def test_unpaid_work_entry(self):
        contract = self.create_contract(date(2015, 1, 24))
        self._adjust_payslip(contract)
        work_entries = self.employee.contract_ids.generate_work_entries(date(2018, 12, 31), date(2019, 12, 31))
        unpaid_work_entry_type = self.env.ref('hr_work_entry_contract.work_entry_type_unpaid_leave')
        work_entry = self.env['hr.work.entry'].create({
            'name': 'Unpaid work entry',
            'employee_id': self.employee.id,
            'contract_id': contract.id,
            'work_entry_type_id': unpaid_work_entry_type.id,
            'date_start': datetime(2019, 3, 1, 7, 0),
            'date_stop': datetime(2019, 3, 10, 18, 0),
        })  # 6 days * 8 hours = 48 hours
        work_entries.filtered(lambda r: r.date_start >= datetime(2019, 3, 1, 7, 0) and r.date_stop <= datetime(2019, 3, 10, 18, 0)).write({'state': 'cancelled'})
        work_entries.filtered(lambda r: r.state == 'confirmed').action_validate()
        work_entry.action_validate()
        # In 2019: 261 days * 8h = 2088 hours
        self.assertAlmostEqual(self.payslip._get_paid_amount(), 2442.53, places=2, msg='It should deduct 48 hours')
