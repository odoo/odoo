# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from pytz import timezone, UTC

from odoo.tests.common import tagged
from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('sa')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.sa'),
            structure=cls.env.ref('l10n_sa_hr_payroll.ksa_saudi_employee_payroll_structure'),
            structure_type=cls.env.ref('l10n_sa_hr_payroll.ksa_employee_payroll_structure_type'),
            contract_fields={
                'wage': 10000.0,
                'l10n_sa_housing_allowance': 400.0,
                'l10n_sa_transportation_allowance': 200.0,
                'l10n_sa_other_allowances': 150.0,
                'l10n_sa_number_of_days': 20.0,
            }
        )
        cls.env.user.groups_id |= cls.env.ref('hr_holidays.group_hr_holidays_manager')

        cls.saudi_work_contact = cls.env['res.partner'].create({
            'name': 'KSA Local Employee',
            'company_id': cls.env.company.id,
        })
        cls.expat_work_contact = cls.env['res.partner'].create({
            'name': 'KSA Expat Employee',
            'company_id': cls.env.company.id,
        })

        cls.saudi_employee = cls.env['hr.employee'].create({
            'name': 'KSA Local Employee',
            'address_id': cls.saudi_work_contact.id,
            'company_id': cls.env.company.id,
            'country_id': cls.env.ref('base.sa').id,
        })

        cls.expat_employee = cls.env['hr.employee'].create({
            'name': 'KSA Expat Employee',
            'address_id': cls.expat_work_contact.id,
            'company_id': cls.env.company.id,
            'country_id': cls.env.ref('base.in').id,  # any other nationality
        })

        cls.saudi_contract = cls.env['hr.contract'].create({
            'name': "KSA Local Employee's contract",
            'employee_id': cls.saudi_employee.id,
            'company_id': cls.env.company.id,
            'structure_type_id': cls.env.ref('l10n_sa_hr_payroll.ksa_employee_payroll_structure_type').id,
            'date_start': date(2024, 1, 1),
            'wage': 12000,
            'l10n_sa_housing_allowance': 1000,
            'l10n_sa_transportation_allowance': 200,
            'l10n_sa_other_allowances': 500,
            'l10n_sa_number_of_days': 21,
            'state': "open",
        })

        cls.expat_contract = cls.env['hr.contract'].create({
            'name': "KSA Expat Employee's contract",
            'employee_id': cls.expat_employee.id,
            'company_id': cls.env.company.id,
            'structure_type_id': cls.env.ref('l10n_sa_hr_payroll.ksa_employee_payroll_structure_type').id,
            'date_start': date(2024, 1, 1),
            'wage': 5000,
            'l10n_sa_housing_allowance': 1000,
            'l10n_sa_transportation_allowance': 200,
            'l10n_sa_other_allowances': 300,
            'l10n_sa_number_of_days': 21,
            'state': "open",
        })

        cls.compensable_timeoff_type = cls.env['hr.leave.type'].create({
            'name': "KSA Compensable Leaves",
            'company_id': cls.env.company.id,
            'l10n_sa_is_compensable': True
        })

        cls.env['hr.leave.allocation'].create({
            'employee_id': cls.saudi_employee.id,
            'date_from': date(2024, 1, 1),
            'holiday_status_id': cls.compensable_timeoff_type.id,
            'number_of_days': 25,
            'state': 'confirm',
        }).action_validate()

    @classmethod
    def _lay_off_employee(cls, saudi_or_expat='saudi', reason=None):
        employee = cls.saudi_employee if saudi_or_expat == 'saudi' else cls.expat_employee
        employee.write({
            'active': False,
            'departure_reason_id': reason,
            'departure_date': date(2024, 3, 31)
        })
        (cls.saudi_contract if saudi_or_expat == 'saudi' else cls.expat_contract).date_end = date(2024, 3, 31)

    def test_saudi_payslip(self):
        payslip = self._generate_payslip(
            date(2024, 1, 1), date(2024, 1, 31),
            employee_id=self.saudi_employee.id,
            contract_id=self.saudi_contract.id,
            struct_id=self.env.ref('l10n_sa_hr_payroll.ksa_saudi_employee_payroll_structure').id)
        payslip_results = {
            'BASIC': 12000.0,
            'GOSI_COMP': -1527.5,
            'GOSI_EMP': -1267.5,
            'HOUALLOW': 1000.0,
            'OTALLOW': 500.0,
            'TRAALLOW': 200.0,
            'EOSP': 799.17,
            'GROSS': 13700.0,
            'NET': 12432.5,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_expat_payslip(self):
        payslip = self._generate_payslip(
            date(2024, 1, 1), date(2024, 1, 31),
            employee_id=self.expat_employee.id,
            contract_id=self.expat_contract.id,
            struct_id=self.env.ref('l10n_sa_hr_payroll.ksa_expat_employee_payroll_structure').id)
        payslip_results = {
            'BASIC': 5000.0,
            'GOSI_COMP': -120.0,
            'HOUALLOW': 1000.0,
            'OTALLOW': 300.0,
            'TRAALLOW': 200.0,
            'EOSP': 379.17,
            'GROSS': 6500.0,
            'NET': 6500.0,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_saudi_payslip_laid_off(self):
        self._lay_off_employee('saudi', self.env.ref('l10n_sa_hr_payroll.saudi_departure_clause_77').id)
        payslip = self._generate_payslip(
            date(2024, 3, 1), date(2024, 3, 31),
            employee_id=self.saudi_employee.id,
            contract_id=self.saudi_contract.id,
            struct_id=self.env.ref('l10n_sa_hr_payroll.ksa_saudi_employee_payroll_structure').id)
        payslip_results = {
            'BASIC': 12000.0,
            'GOSI_COMP': -1527.5,
            'GOSI_EMP': -1267.5,
            'HOUALLOW': 1000.0,
            'OTALLOW': 500.0,
            'TRAALLOW': 200.0,
            'EOSALLOW': 27400.0,
            'EOSB': 13700.0,
            'ANNUALCOMP': 11416.67,
            'GROSS': 54800.0,
            'NET': 53532.5,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_expat_payslip_laid_off(self):
        self._lay_off_employee('expat', self.env.ref('l10n_sa_hr_payroll.saudi_departure_end_of_contract').id)
        payslip = self._generate_payslip(
            date(2024, 3, 1), date(2024, 3, 31),
            employee_id=self.expat_employee.id,
            contract_id=self.expat_contract.id,
            struct_id=self.env.ref('l10n_sa_hr_payroll.ksa_expat_employee_payroll_structure').id)
        payslip_results = {
            'BASIC': 5000.0,
            'GOSI_COMP': -120.0,
            'HOUALLOW': 1000.0,
            'OTALLOW': 300.0,
            'TRAALLOW': 200.0,
            'EOSB': 812.5,
            'GROSS': 7312.5,
            'NET': 7312.5,
        }
        self._validate_payslip(payslip, payslip_results)

    def test_payslip_overtime_1(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        work_entry = self.env['hr.work.entry'].create({
            'name': 'OT',
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'date_start': datetime(2024, 1, 1, 18, 0, tzinfo=timezone(self.tz)).astimezone(tz=UTC).replace(tzinfo=None),
            'date_stop': datetime(2024, 1, 1, 22, 0, tzinfo=timezone(self.tz)).astimezone(tz=UTC).replace(tzinfo=None),
            'work_entry_type_id': self.env.ref('hr_work_entry.overtime_work_entry_type').id,
        })
        work_entry.action_validate()
        payslip.compute_sheet()
        payslip_results = {'BASIC': 10000.0, 'GOSI_COMP': -1222.0, 'GOSI_EMP': -1014.0, 'HOUALLOW': 400.0, 'OTALLOW': 150.0, 'TRAALLOW': 200.0, 'EOSP': 597.22, 'GROSS': 10750.0, 'NET': 9736.0}
        self._validate_payslip(payslip, payslip_results)
