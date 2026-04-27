# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo.tests.common import tagged
from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon


@tagged('post_install_l10n', 'post_install', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('nl')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.nl'),
            structure=cls.env.ref('l10n_nl_hr_payroll.hr_payroll_structure_nl_employee_salary'),
            structure_type=cls.env.ref('l10n_nl_hr_payroll.structure_type_employee_nl'),
            contract_fields={
                'wage': 5000,
                'structure_type_id': cls.env.ref('l10n_nl_hr_payroll.structure_type_employee_nl').id
            }
        )

    def test_regular_payslip_resident(self):
        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 0)

        self._validate_worked_days(payslip, {'WORK100': (22.0, 176.0, 5000)})

        payslip_results = {'BASIC': 5000.0, 'GROSS': 5000.0, 'AOW': -524.01, 'Anw': -2.93, 'Wlz': -282.5, 'TAXABLE': 4190.57, 'INCOMETAX': -724.02, 'Zvw': -323.91, 'WW': -132.0, 'WWFund': -35.89, 'WAO/WIA': -324.38, 'Whk': -58.26, 'NET': 3466.55}
        self._validate_payslip(payslip, payslip_results)

    def test_regular_payslip_non_resident(self):
        self.employee.is_non_resident = True
        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 0)

        self._validate_worked_days(payslip, {'WORK100': (22.0, 176.0, 5000)})

        payslip_results = {'BASIC': 5000.0, 'GROSS': 5000.0, 'AOW': -524.01, 'Anw': -29.27, 'Wlz': -282.5, 'TAXABLE': 4164.22, 'INCOMETAX': -714.29, 'Zvw': -323.91, 'WW': -132.0, 'WWFund': -35.89, 'WAO/WIA': -324.38, 'Whk': -58.26, 'NET': 3449.93}
        self._validate_payslip(payslip, payslip_results)

    def test_regular_payslip_30_percent(self):

        self.employee.is_non_resident = True
        self.contract.l10n_nl_30_percent = True
        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 0)

        self._validate_worked_days(payslip, {'WORK100': (22.0, 176.0, 5000)})

        payslip_results = {'BASIC': 5000.0, 'GROSS': 5000.0, 'AOW': -524.01, 'Anw': -29.27, 'Wlz': -282.5, 'TAXABLE': 2664.22, 'INCOMETAX': -247.24, 'Zvw': -236.25, 'WW': -92.4, 'WWFund': -26.95, 'WAO/WIA': -248.85, 'Whk': -58.26, 'NET': 3916.98}
        self._validate_payslip(payslip, payslip_results)

    def test_regular_payslip_30_percent_low_salary(self):
        self.employee.is_non_resident = True
        self.contract.l10n_nl_30_percent = True
        self.contract.wage = 1500
        payslip = self._generate_payslip(datetime.date(2023, 1, 1), datetime.date(2023, 1, 31))

        self.assertEqual(len(payslip.worked_days_line_ids), 1)
        self.assertEqual(len(payslip.input_line_ids), 0)

        self._validate_worked_days(payslip, {'WORK100': (22.0, 176.0, 1500)})

        payslip_results = {'BASIC': 1500.0, 'GROSS': 1500.0, 'AOW': -187.95, 'Anw': -10.5, 'Wlz': -101.33, 'TAXABLE': 750.23, 'INCOMETAX': -69.62, 'Zvw': -70.88, 'WW': -27.72, 'WWFund': -8.09, 'WAO/WIA': -74.66, 'Whk': -58.26, 'NET': 1130.6}
        self._validate_payslip(payslip, payslip_results)
