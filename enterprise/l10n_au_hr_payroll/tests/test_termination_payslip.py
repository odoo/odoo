# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import date
from unittest.mock import patch
from freezegun import freeze_time

from odoo import fields
from odoo.tests import tagged
from .common import TestPayrollCommon


def _patched_ytd(self, **kwargs):
    totals = {
        "slip_lines": defaultdict(lambda: defaultdict(float)),
        "worked_days": defaultdict(lambda: defaultdict(float)),
        "periods": 1,
        "fields": defaultdict(float),
    }
    totals["slip_lines"]["GROSS"]["total"] = 49000
    return totals


@tagged("post_install_l10n", "post_install", "-at_install", "l10n_au_hr_payroll")
class TestPayrollTerminationPayment(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.startClassPatcher(freeze_time(date(2024, 1, 1)))
        # cls.default_payroll_structure = cls.env.ref("l10n_au_hr_payroll.hr_payroll_structure_au_regular")
        cls.tax_treatment_category = 'R'

    def test_termination_payslip_1(self):
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'l10n_au_tax_free_threshold': True,
            'leave_loading': 'regular',
            'leave_loading_rate': 17.5,
            'salary_sacrifice_superannuation': 77,
            'salary_sacrifice_other': 0,
            'schedule_pay': 'weekly',
            'wage': 1384.72,
            'casual_loading': 0,
        })
        # Gives four day of leaves to the employee.
        self.env['hr.leave.allocation'].create([{
            'name': 'Paid Time Off 2023-24',
            'holiday_status_id': self.annual_leave_type.id,
            'number_of_days': 5,
            'employee_id': employee.id,
            'state': 'confirm',
            'date_from': date(2023, 7, 1),
            'date_to': date(2024, 6, 30),
        }]).action_validate()
        # Use two day leaves in the payslip period leaving two unused day leave.
        leave = self.env['hr.leave'].create({
            'name': 'Holiday Request',
            'employee_id': employee.id,
            'holiday_status_id': self.annual_leave_type.id,
            'request_date_from': date(2023, 7, 6),
            'request_date_to': date(2023, 7, 7),
        })
        leave.action_approve(check_state=False)
        # Regenerate work entries
        self.env['hr.work.entry'].search([('employee_id', '=', employee.id)]).unlink()
        payslip_date = date(2023, 7, 3)
        payslip_end_date = date(2023, 7, 9)
        work_entries = contract.generate_work_entries(payslip_date, payslip_end_date)
        work_entries.action_validate()

        # This would be done by the wizard.
        contract.date_end = date(2023, 7, 9)

        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 3, 22.8, 830.83),
                (self.work_entry_types['AU.PT'].id, 2, 15.2, 650.82),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 1481.65),
                ('OTE', 1481.65),
                ('SALARY.SACRIFICE.TOTAL', -77),
                ('GROSS', 1404.65),
                ('ETP.GROSS', 250),
                ('ETP.TAXFREE', 0),
                ('ETP.TAXABLE', 250),
                ('ETP.LEAVE.GROSS', 976.23),
                ('WITHHOLD', -302),
                ('WITHHOLD.STUDY', -49),
                ('MEDICARE', 0),
                ('ETP.WITHHOLD', -80),
                ('ETP.LEAVE.WITHHOLD', -364),
                ('WITHHOLD.TOTAL', -795),
                ('NET', 1835.88),
                ('SUPER.CONTRIBUTION', 77),
                ('SUPER', 162.98),
            ],
            input_lines=[{
                'input_type_id': self.env.ref('l10n_au_hr_payroll.input_golden_handshake').id,
                'amount': 250,
            }],
            payslip_date_from=payslip_date,
            payslip_date_to=payslip_end_date,
            termination_type="normal"
        )

    def test_termination_withholding_1(self):
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'l10n_au_tax_free_threshold': True,
            'leave_loading': 'once',
            'leave_loading_rate': 17.5,
            'salary_sacrifice_superannuation': 77,
            'salary_sacrifice_other': 0,
            'schedule_pay': 'monthly',
            'wage': 7000,
            'casual_loading': 0,
            'tax_treatment_category': 'V',
            'birthday': fields.Date.to_date('1987-05-09'),
            'contract_date_start': fields.Date.to_date('2015-01-01'),

        })
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 19.0, 144.4, 6138.44),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 6138.44),
                ('OTE', 6138.44),
                ('SALARY.SACRIFICE.TOTAL', -77.00),
                ('GROSS', 6061.44),
                ('ETP.GROSS', 120000.00),
                ('ETP.TAXFREE', 65931.00),
                ('ETP.TAXABLE', 54069.00),
                ('ETP.LEAVE.GROSS', 0.00),
                ('WITHHOLD', -1300.00),
                ('WITHHOLD.STUDY', -212.00),
                ('MEDICARE', 0.00),
                ('ETP.WITHHOLD', -17302.00),
                ('ETP.LEAVE.WITHHOLD', -0.00),
                ('WITHHOLD.TOTAL', -18814.00),
                ('NET', 107247.44),
                ('SUPER.CONTRIBUTION', 77.00),
                ('SUPER', 675.23),
            ],
            input_lines=[{
                'input_type_id': self.env.ref('l10n_au_hr_payroll.input_genuine_redundancy').id,
                'amount': 120000,
            }],
            payslip_date_from=fields.Date.to_date('2024-02-01'),
            payslip_date_to=fields.Date.to_date('2024-02-27'),
            termination_type="normal"
        )

    def test_termination_withholding_2(self):
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'l10n_au_tax_free_threshold': True,
            'leave_loading': 'once',
            'leave_loading_rate': 17.5,
            'salary_sacrifice_superannuation': 77,
            'salary_sacrifice_other': 0,
            'schedule_pay': 'monthly',
            'wage': 7000,
            'casual_loading': 0,
            'tax_treatment_category': 'V',
            'birthday': fields.Date.to_date('1964-08-01'),
            'contract_date_start': fields.Date.to_date('2015-01-01'),

        })
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 19.0, 144.4, 6138.44),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 6138.44),
                ('OTE', 6138.44),
                ('SALARY.SACRIFICE.TOTAL', -77.00),
                ('GROSS', 6061.44),
                ('ETP.GROSS', 120000.00),
                ('ETP.TAXFREE', 65931.00),
                ('ETP.TAXABLE', 54069.00),
                ('ETP.LEAVE.GROSS', 0.00),
                ('WITHHOLD', -1300.00),
                ('WITHHOLD.STUDY', -212.00),
                ('MEDICARE', 0.00),
                ('ETP.WITHHOLD', -17302.00),
                ('ETP.LEAVE.WITHHOLD', -0.00),
                ('WITHHOLD.TOTAL', -18814.00),
                ('NET', 107247.44),
                ('SUPER.CONTRIBUTION', 77.00),
                ('SUPER', 675.23),
            ],
            input_lines=[{
                'input_type_id': self.env.ref('l10n_au_hr_payroll.input_early_retirement_scheme').id,
                'amount': 120000,
            }],
            payslip_date_from=fields.Date.to_date('2024-02-01'),
            payslip_date_to=fields.Date.to_date('2024-02-27'),
            termination_type="normal"
        )

    def test_termination_withholding_3(self):
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'l10n_au_tax_free_threshold': True,
            'leave_loading': 'once',
            'leave_loading_rate': 17.5,
            'salary_sacrifice_superannuation': 77,
            'salary_sacrifice_other': 0,
            'schedule_pay': 'monthly',
            'wage': 7000,
            'casual_loading': 0,
            'tax_treatment_category': 'V',
            'birthday': fields.Date.to_date('1998-07-25'),
            'contract_date_start': fields.Date.to_date('2015-01-01'),

        })
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 19.0, 144.4, 6138.44),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 6138.44),
                ('OTE', 6138.44),
                ('SALARY.SACRIFICE.TOTAL', -77.00),
                ('GROSS', 6061.44),
                ('ETP.GROSS', 50000.00),
                ('ETP.TAXFREE', 0.00),
                ('ETP.TAXABLE', 50000.00),
                ('ETP.LEAVE.GROSS', 0.00),
                ('WITHHOLD', -1300.00),
                ('WITHHOLD.STUDY', -212.00),
                ('MEDICARE', 0.00),
                ('ETP.WITHHOLD', -16000.00),
                ('ETP.LEAVE.WITHHOLD', -0.00),
                ('WITHHOLD.TOTAL', -17512.00),
                ('NET', 38549.44),
                ('SUPER.CONTRIBUTION', 77.00),
                ('SUPER', 675.23),
            ],
            input_lines=[{
                'input_type_id': self.env.ref('l10n_au_hr_payroll.input_harassment').id,
                'amount': 50000,
            }],
            payslip_date_from=fields.Date.to_date('2024-02-01'),
            payslip_date_to=fields.Date.to_date('2024-02-27'),
            termination_type="normal"
        )

    def test_termination_withholding_4(self):
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'l10n_au_tax_free_threshold': True,
            'leave_loading': 'once',
            'leave_loading_rate': 17.5,
            'salary_sacrifice_superannuation': 77,
            'salary_sacrifice_other': 0,
            'schedule_pay': 'monthly',
            'wage': 7000,
            'casual_loading': 0,
            'tax_treatment_category': 'V',
            'birthday': fields.Date.to_date('1975-01-01'),
            'contract_date_start': fields.Date.to_date('2015-01-01'),

        })
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 19.0, 144.4, 6138.44),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 6138.44),
                ('OTE', 6138.44),
                ('SALARY.SACRIFICE.TOTAL', -77.00),
                ('GROSS', 6061.44),
                ('ETP.GROSS', 120000.00),
                ('ETP.TAXFREE', 0.00),
                ('ETP.TAXABLE', 120000.00),
                ('ETP.LEAVE.GROSS', 0.00),
                ('WITHHOLD', -1300.00),
                ('WITHHOLD.STUDY', -212.00),
                ('MEDICARE', 0.00),
                ('ETP.WITHHOLD', -38400.00),
                ('ETP.LEAVE.WITHHOLD', -0.00),
                ('WITHHOLD.TOTAL', -39912.00),
                ('NET', 86149.44),
                ('SUPER.CONTRIBUTION', 77.00),
                ('SUPER', 675.23),
            ],
            input_lines=[{
                'input_type_id': self.env.ref('l10n_au_hr_payroll.input_golden_handshake').id,
                'amount': 120000,
            }],
            payslip_date_from=fields.Date.to_date('2024-02-01'),
            payslip_date_to=fields.Date.to_date('2024-02-27'),
            termination_type="normal"
        )

    # Patching is faster than generating payslip for the ytd, and has the same effect.
    @patch('odoo.addons.l10n_au_hr_payroll.models.hr_payslip.HrPayslip._l10n_au_get_year_to_date_totals', _patched_ytd)
    def test_termination_withholding_5(self):
        # We need the ytd total for this test.
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'l10n_au_tax_free_threshold': True,
            'leave_loading': 'once',
            'leave_loading_rate': 17.5,
            'salary_sacrifice_superannuation': 77,
            'salary_sacrifice_other': 0,
            'schedule_pay': 'monthly',
            'wage': 7000,
            'casual_loading': 0,
            'tax_treatment_category': 'V',
            'birthday': fields.Date.to_date('1975-01-01'),
            'contract_date_start': fields.Date.to_date('2015-01-01'),

        })
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 19.0, 144.4, 6138.44),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 6138.44),
                ('OTE', 6138.44),
                ('SALARY.SACRIFICE.TOTAL', -77.00),
                ('GROSS', 6061.44),
                ('ETP.GROSS', 200000.00),
                ('ETP.TAXFREE', 0.00),
                ('ETP.TAXABLE', 200000.00),
                ('ETP.LEAVE.GROSS', 0.00),
                ('WITHHOLD', -1300.00),
                ('WITHHOLD.STUDY', -212.00),
                ('MEDICARE', 0.00),
                ('ETP.WITHHOLD', -74350.00),
                ('ETP.LEAVE.WITHHOLD', -0.00),
                ('WITHHOLD.TOTAL', -75862.00),
                ('NET', 130199.44),
                ('SUPER.CONTRIBUTION', 77.00),
                ('SUPER', 675.23),
            ],
            input_lines=[{
                'input_type_id': self.env.ref('l10n_au_hr_payroll.input_golden_handshake').id,
                'amount': 200000,
            }],
            payslip_date_from=fields.Date.to_date('2024-02-01'),
            payslip_date_to=fields.Date.to_date('2024-02-27'),
            termination_type="normal"
        )

    def test_termination_withholding_6(self):
        # We need the ytd total for this test.
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'l10n_au_tax_free_threshold': True,
            'leave_loading': 'once',
            'leave_loading_rate': 17.5,
            'salary_sacrifice_superannuation': 77,
            'salary_sacrifice_other': 0,
            'schedule_pay': 'monthly',
            'wage': 11000,
            'casual_loading': 0,
            'tax_treatment_category': 'V',
            'birthday': fields.Date.to_date('1975-01-01'),
            'contract_date_start': fields.Date.to_date('2015-01-01'),

        })
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 19.0, 144.4, 9645.92),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 9645.92),
                ('OTE', 9645.92),
                ('SALARY.SACRIFICE.TOTAL', -77.00),
                ('GROSS', 9568.92),
                ('ETP.GROSS', 250000.00),
                ('ETP.TAXFREE', 0.00),
                ('ETP.TAXABLE', 250000.00),
                ('ETP.LEAVE.GROSS', 0.00),
                ('WITHHOLD', -2509.00),
                ('WITHHOLD.STUDY', -719.00),
                ('MEDICARE', 0.00),
                ('ETP.WITHHOLD', -82250.00),
                ('ETP.LEAVE.WITHHOLD', -0.00),
                ('WITHHOLD.TOTAL', -85478.00),
                ('NET', 174090.92),
                ('SUPER.CONTRIBUTION', 77.00),
                ('SUPER', 1061.05),
            ],
            input_lines=[{
                'input_type_id': self.env.ref('l10n_au_hr_payroll.input_discrimination').id,
                'amount': 250000,
            }],
            payslip_date_from=fields.Date.to_date('2024-02-01'),
            payslip_date_to=fields.Date.to_date('2024-02-27'),
            termination_type="normal"
        )

    def test_termination_withholding_7(self):
        # We need the ytd total for this test.
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'l10n_au_tax_free_threshold': True,
            'leave_loading': 'once',
            'leave_loading_rate': 17.5,
            'salary_sacrifice_superannuation': 77,
            'salary_sacrifice_other': 0,
            'schedule_pay': 'monthly',
            'wage': 7000,
            'casual_loading': 0,
            'tax_treatment_category': 'V',
            'birthday': fields.Date.to_date('1975-01-01'),
            'contract_date_start': fields.Date.to_date('2015-01-01'),

        })
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 19.0, 144.4, 6138.44),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 6138.44),
                ('OTE', 13138.44),
                ('SALARY.SACRIFICE.TOTAL', -77.00),
                ('GROSS', 6061.44),
                ('ETP.GROSS', 7000.00),
                ('ETP.TAXFREE', 0.00),
                ('ETP.TAXABLE', 7000.00),
                ('ETP.LEAVE.GROSS', 0.00),
                ('WITHHOLD', -1300.00),
                ('WITHHOLD.STUDY', -212.00),
                ('MEDICARE', 0.00),
                ('ETP.WITHHOLD', -2240.0),
                ('ETP.LEAVE.WITHHOLD', -0.00),
                ('WITHHOLD.TOTAL', -3752),
                ('NET', 9309.44),
                ('SUPER.CONTRIBUTION', 77.00),
                ('SUPER', 1445.23),
            ],
            input_lines=[{
                'input_type_id': self.env.ref('l10n_au_hr_payroll.input_in_lieu_of_notice').id,
                'amount': 7000,
            }],
            payslip_date_from=fields.Date.to_date('2024-02-01'),
            payslip_date_to=fields.Date.to_date('2024-02-27'),
            termination_type="normal"
        )

    def test_termination_withholding_8(self):
        # We need the ytd total for this test.
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'l10n_au_tax_free_threshold': True,
            'leave_loading': 'once',
            'leave_loading_rate': 17.5,
            'salary_sacrifice_superannuation': 77,
            'salary_sacrifice_other': 0,
            'schedule_pay': 'monthly',
            'wage': 7000,
            'casual_loading': 0,
            'tax_treatment_category': 'V',
            'birthday': fields.Date.to_date('1959-01-01'),
            'contract_date_start': fields.Date.to_date('2015-01-01'),

        })
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 19.0, 144.4, 6138.44),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 6138.44),
                ('OTE', 6138.44),
                ('SALARY.SACRIFICE.TOTAL', -77.00),
                ('GROSS', 6061.44),
                ('ETP.GROSS', 120000.00),
                ('ETP.TAXFREE', 0.00),
                ('ETP.TAXABLE', 120000.00),
                ('ETP.LEAVE.GROSS', 0.00),
                ('WITHHOLD', -1300.00),
                ('WITHHOLD.STUDY', -212.00),
                ('MEDICARE', 0.00),
                ('ETP.WITHHOLD', -20400),
                ('ETP.LEAVE.WITHHOLD', -0.00),
                ('WITHHOLD.TOTAL', -21912),
                ('NET', 104149.44),
                ('SUPER.CONTRIBUTION', 77.00),
                ('SUPER', 675.23),
            ],
            input_lines=[{
                'input_type_id': self.env.ref('l10n_au_hr_payroll.input_non_genuine_redundancy').id,
                'amount': 120000,
            }],
            payslip_date_from=fields.Date.to_date('2024-02-01'),
            payslip_date_to=fields.Date.to_date('2024-02-27'),
            termination_type="normal"
        )

    def test_termination_withholding_9(self):
        # We need the ytd total for this test.
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'l10n_au_tax_free_threshold': True,
            'leave_loading': 'once',
            'leave_loading_rate': 17.5,
            'salary_sacrifice_superannuation': 77,
            'salary_sacrifice_other': 0,
            'schedule_pay': 'monthly',
            'wage': 7000,
            'casual_loading': 0,
            'tax_treatment_category': 'V',
            'birthday': fields.Date.to_date('1963-01-01'),
            'contract_date_start': fields.Date.to_date('2015-01-01'),

        })
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 19.0, 144.4, 6138.44),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 6138.44),
                ('OTE', 6138.44),
                ('SALARY.SACRIFICE.TOTAL', -77.00),
                ('GROSS', 6061.44),
                ('ETP.GROSS', 120000.00),
                ('ETP.TAXFREE', 0.00),
                ('ETP.TAXABLE', 120000.00),
                ('ETP.LEAVE.GROSS', 0.00),
                ('WITHHOLD', -1300.00),
                ('WITHHOLD.STUDY', -212.00),
                ('MEDICARE', 0.00),
                ('ETP.WITHHOLD', -20400),
                ('ETP.LEAVE.WITHHOLD', -0.00),
                ('WITHHOLD.TOTAL', -21912),
                ('NET', 104149.44),
                ('SUPER.CONTRIBUTION', 77.00),
                ('SUPER', 675.23),
            ],
            input_lines=[{
                'input_type_id': self.env.ref('l10n_au_hr_payroll.input_personal_injury').id,
                'amount': 120000,
            }],
            payslip_date_from=fields.Date.to_date('2024-02-01'),
            payslip_date_to=fields.Date.to_date('2024-02-27'),
            termination_type="normal"
        )

    @patch('odoo.addons.l10n_au_hr_payroll.models.hr_payslip.HrPayslip._l10n_au_get_year_to_date_totals', _patched_ytd)
    def test_termination_withholding_10(self):
        # We need the ytd total for this test.
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'l10n_au_tax_free_threshold': True,
            'leave_loading': 'once',
            'leave_loading_rate': 17.5,
            'salary_sacrifice_superannuation': 77,
            'salary_sacrifice_other': 0,
            'schedule_pay': 'monthly',
            'wage': 7000,
            'casual_loading': 0,
            'tax_treatment_category': 'V',
            'birthday': fields.Date.to_date('1963-01-01'),
            'contract_date_start': fields.Date.to_date('2015-01-01'),

        })
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 19.0, 144.4, 6138.44),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 6138.44),
                ('OTE', 6138.44),
                ('SALARY.SACRIFICE.TOTAL', -77.00),
                ('GROSS', 6061.44),
                ('ETP.GROSS', 170000.00),
                ('ETP.TAXFREE', 0.00),
                ('ETP.TAXABLE', 170000.00),
                ('ETP.LEAVE.GROSS', 0.00),
                ('WITHHOLD', -1300.00),
                ('WITHHOLD.STUDY', -212.00),
                ('MEDICARE', 0.00),
                ('ETP.WITHHOLD', -40600.00),
                ('ETP.LEAVE.WITHHOLD', -0.00),
                ('WITHHOLD.TOTAL', -42112.00),
                ('NET', 133949.44),
                ('SUPER.CONTRIBUTION', 77.00),
                ('SUPER', 675.23),
            ],
            input_lines=[{
                'input_type_id': self.env.ref('l10n_au_hr_payroll.input_non_genuine_redundancy').id,
                'amount': 170000,
            }],
            payslip_date_from=fields.Date.to_date('2024-02-01'),
            payslip_date_to=fields.Date.to_date('2024-02-27'),
            termination_type="normal"
        )

    def test_termination_withholding_11(self):
        # We need the ytd total for this test.
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'l10n_au_tax_free_threshold': True,
            'leave_loading': 'once',
            'leave_loading_rate': 17.5,
            'salary_sacrifice_superannuation': 77,
            'salary_sacrifice_other': 0,
            'schedule_pay': 'monthly',
            'wage': 7000,
            'casual_loading': 0,
            'tax_treatment_category': 'V',
            'birthday': fields.Date.to_date('1963-01-01'),
            'contract_date_start': fields.Date.to_date('2015-01-01'),

        })
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 19.0, 144.4, 6138.44),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 6138.44),
                ('OTE', 6138.44),
                ('SALARY.SACRIFICE.TOTAL', -77.00),
                ('GROSS', 6061.44),
                ('ETP.GROSS', 250000.00),
                ('ETP.TAXFREE', 0.00),
                ('ETP.TAXABLE', 250000.00),
                ('ETP.LEAVE.GROSS', 0.00),
                ('WITHHOLD', -1300.00),
                ('WITHHOLD.STUDY', -212.00),
                ('MEDICARE', 0.00),
                ('ETP.WITHHOLD', -47000.00),
                ('ETP.LEAVE.WITHHOLD', -0.00),
                ('WITHHOLD.TOTAL', -48512.00),
                ('NET', 207549.44),
                ('SUPER.CONTRIBUTION', 77.00),
                ('SUPER', 675.23),
            ],
            input_lines=[{
                'input_type_id': self.env.ref('l10n_au_hr_payroll.input_personal_injury').id,
                'amount': 250000,
            }],
            payslip_date_from=fields.Date.to_date('2024-02-01'),
            payslip_date_to=fields.Date.to_date('2024-02-27'),
            termination_type="normal"
        )

    def test_termination_withholding_12(self):
        # We need the ytd total for this test.
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'non_resident': True,
            'leave_loading': 'once',
            'leave_loading_rate': 17.5,
            'salary_sacrifice_superannuation': 77,
            'salary_sacrifice_other': 0,
            'schedule_pay': 'monthly',
            'wage': 7000,
            'casual_loading': 0,
            'birthday': fields.Date.to_date('1975-01-01'),
            'contract_date_start': fields.Date.to_date('2023-11-01'),
            'tfn_declaration': 'provided',
            'tfn': '999999661',
        })
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 19.0, 144.4, 6138.44),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 6138.44),
                ('OTE', 6138.44),
                ('SALARY.SACRIFICE.TOTAL', -77.00),
                ('GROSS', 6061.44),
                ('ETP.GROSS', 15000.00),
                ('ETP.TAXFREE', 0.00),
                ('ETP.TAXABLE', 15000.00),
                ('ETP.LEAVE.GROSS', 0.00),
                ('WITHHOLD', -1967.00),
                ('WITHHOLD.STUDY', -212.00),
                ('ETP.WITHHOLD', -4500.00),
                ('ETP.LEAVE.WITHHOLD', -0.00),
                ('WITHHOLD.TOTAL', -6679.00),
                ('NET', 14382.44),
                ('SUPER.CONTRIBUTION', 77.00),
                ('SUPER', 675.23),
            ],
            input_lines=[{
                'input_type_id': self.env.ref('l10n_au_hr_payroll.input_non_genuine_redundancy').id,
                'amount': 15000,
            }],
            payslip_date_from=fields.Date.to_date('2024-02-01'),
            payslip_date_to=fields.Date.to_date('2024-02-27'),
            termination_type="normal"
        )

    def test_termination_withholding_13(self):
        # We need the ytd total for this test.
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'tfn_declaration': '000000000',
            'l10n_au_tax_free_threshold': True,
            'leave_loading': 'once',
            'leave_loading_rate': 17.5,
            'salary_sacrifice_superannuation': 77,
            'salary_sacrifice_other': 0,
            'schedule_pay': 'monthly',
            'wage': 7000,
            'casual_loading': 0,
            'tax_treatment_category': 'V',
            'birthday': fields.Date.to_date('1975-01-01'),
            'contract_date_start': fields.Date.to_date('2015-11-01'),
        })
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 19.0, 144.4, 6138.44),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 6138.44),
                ('OTE', 6138.44),
                ('SALARY.SACRIFICE.TOTAL', -77.00),
                ('GROSS', 6061.44),
                ('ETP.GROSS', 15000.00),
                ('ETP.TAXFREE', 0.00),
                ('ETP.TAXABLE', 15000.00),
                ('ETP.LEAVE.GROSS', 0.00),
                ('WITHHOLD', -2848),
                ('WITHHOLD.STUDY', -212.00),
                ('MEDICARE', 0.00),
                ('ETP.WITHHOLD', -7050.00),
                ('ETP.LEAVE.WITHHOLD', -0.00),
                ('WITHHOLD.TOTAL', -10110),
                ('NET', 10951.44),
                ('SUPER.CONTRIBUTION', 77.00),
                ('SUPER', 675.23),
            ],
            input_lines=[{
                'input_type_id': self.env.ref('l10n_au_hr_payroll.input_non_genuine_redundancy').id,
                'amount': 15000,
            }],
            payslip_date_from=fields.Date.to_date('2024-02-01'),
            payslip_date_to=fields.Date.to_date('2024-02-27'),
            termination_type="normal"
        )

    def test_termination_withholding_14(self):
        # We need the ytd total for this test.
        employee, contract = self._create_employee(contract_info={
            'employee': 'Test Employee',
            'employment_basis_code': 'F',
            'leave_loading': 'once',
            'leave_loading_rate': 17.5,
            'salary_sacrifice_superannuation': 77,
            'salary_sacrifice_other': 0,
            'schedule_pay': 'monthly',
            'wage': 7000,
            'casual_loading': 0,
            'birthday': fields.Date.to_date('1975-01-01'),
            'contract_date_start': fields.Date.to_date('2023-11-01'),
            'tfn_declaration': '000000000',
            'non_resident': True,
        })
        self._test_payslip(
            employee,
            contract,
            expected_worked_days=[
                # (work_entry_type_id.id, number_of_day, number_of_hours, amount)
                (self.work_entry_types['WORK100'].id, 19.0, 144.4, 6138.44),
            ],
            expected_lines=[
                # (code, total)
                ('BASIC', 6138.44),
                ('OTE', 6138.44),
                ('SALARY.SACRIFICE.TOTAL', -77.00),
                ('GROSS', 6061.44),
                ('ETP.GROSS', 15000.00),
                ('ETP.TAXFREE', 0.00),
                ('ETP.TAXABLE', 15000.00),
                ('ETP.LEAVE.GROSS', 0.00),
                ('WITHHOLD', -2727),
                ('WITHHOLD.STUDY', -212.0),
                ('ETP.WITHHOLD', -6750.00),
                ('ETP.LEAVE.WITHHOLD', -0.00),
                ('WITHHOLD.TOTAL', -9689),
                ('NET', 11372.44),
                ('SUPER.CONTRIBUTION', 77.00),
                ('SUPER', 675.23),
            ],
            input_lines=[{
                'input_type_id': self.env.ref('l10n_au_hr_payroll.input_non_genuine_redundancy').id,
                'amount': 15000,
            }],
            payslip_date_from=fields.Date.to_date('2024-02-01'),
            payslip_date_to=fields.Date.to_date('2024-02-27'),
            termination_type="normal"
        )
