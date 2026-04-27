# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date

from odoo.addons.l10n_ch_hr_payroll_elm_transmission.tests.swissdec_5_0 import TestSwissdec5Common
from odoo.tests.common import tagged
from odoo.tools import file_open

from freezegun import freeze_time
import json


@tagged('post_install_l10n', 'post_install', '-at_install', 'swissdec_payroll')
class TestSwissdecTestCases(TestSwissdec5Common):
    @freeze_time("2024-01-01")
    def test_yearly_retrospective_2021_11(self):
        identifier = "yearly_retrospective_2021_11"
        generated_dict = self.yearly_retrospective_2021_11._get_declaration()
        self._compare_with_truth_base("yearly_retrospective", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_2021_12(self):
        identifier = "yearly_retrospective_2021_12"
        generated_dict = self.yearly_retrospective_2021_12._get_declaration()
        self._compare_with_truth_base("yearly_retrospective", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_2022_01(self):
        identifier = "yearly_retrospective_2022_01"
        generated_dict = self.yearly_retrospective_2022_01._get_declaration()
        self._compare_with_truth_base("yearly_retrospective", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_2022_02(self):
        identifier = "yearly_retrospective_2022_02"
        generated_dict = self.yearly_retrospective_2022_02._get_declaration()
        self._compare_with_truth_base("yearly_retrospective", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_2022_03(self):
        identifier = "yearly_retrospective_2022_03"
        generated_dict = self.yearly_retrospective_2022_03._get_declaration()
        self._compare_with_truth_base("yearly_retrospective", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_2022_04(self):
        identifier = "yearly_retrospective_2022_04"
        generated_dict = self.yearly_retrospective_2022_04._get_declaration()
        self._compare_with_truth_base("yearly_retrospective", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_2022_05(self):
        identifier = "yearly_retrospective_2022_05"
        generated_dict = self.yearly_retrospective_2022_05._get_declaration()
        self._compare_with_truth_base("yearly_retrospective", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_2022_06(self):
        identifier = "yearly_retrospective_2022_06"
        generated_dict = self.yearly_retrospective_2022_06._get_declaration()
        self._compare_with_truth_base("yearly_retrospective", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_2022_07(self):
        identifier = "yearly_retrospective_2022_07"
        generated_dict = self.yearly_retrospective_2022_07._get_declaration()
        self._compare_with_truth_base("yearly_retrospective", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_2022_08(self):
        identifier = "yearly_retrospective_2022_08"
        generated_dict = self.yearly_retrospective_2022_08._get_declaration()
        self._compare_with_truth_base("yearly_retrospective", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_2022_09(self):
        identifier = "yearly_retrospective_2022_09"
        generated_dict = self.yearly_retrospective_2022_09._get_declaration()
        self._compare_with_truth_base("yearly_retrospective", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_2022_10(self):
        identifier = "yearly_retrospective_2022_10"
        generated_dict = self.yearly_retrospective_2022_10._get_declaration()
        self._compare_with_truth_base("yearly_retrospective", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_2022_11(self):
        identifier = "yearly_retrospective_2022_11"
        generated_dict = self.yearly_retrospective_2022_11._get_declaration()
        self._compare_with_truth_base("yearly_retrospective", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_2022_12(self):
        identifier = "yearly_retrospective_2022_12"
        generated_dict = self.yearly_retrospective_2022_12._get_declaration()
        self._compare_with_truth_base("yearly_retrospective", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_2023_01(self):
        identifier = "yearly_retrospective_2023_01"
        generated_dict = self.yearly_retrospective_2023_01._get_declaration()
        self._compare_with_truth_base("yearly_retrospective", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_2023_02(self):
        identifier = "yearly_retrospective_2023_02"
        generated_dict = self.yearly_retrospective_2023_02._get_declaration()
        self._compare_with_truth_base("yearly_retrospective", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_ema_declaration_2021_11(self):
        identifier = "ema_declaration_2021_11"
        generated_dict = self.ema_declaration_2021_11._get_declaration()
        self._compare_with_truth_base("ema_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_ema_declaration_2021_12(self):
        identifier = "ema_declaration_2021_12"
        generated_dict = self.ema_declaration_2021_12._get_declaration()
        self._compare_with_truth_base("ema_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_ema_declaration_2022_01(self):
        identifier = "ema_declaration_2022_01"
        generated_dict = self.ema_declaration_2022_01._get_declaration()
        self._compare_with_truth_base("ema_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_ema_declaration_2022_02(self):
        identifier = "ema_declaration_2022_02"
        generated_dict = self.ema_declaration_2022_02._get_declaration()
        self._compare_with_truth_base("ema_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_ema_declaration_2022_03(self):
        identifier = "ema_declaration_2022_03"
        generated_dict = self.ema_declaration_2022_03._get_declaration()
        self._compare_with_truth_base("ema_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_ema_declaration_2022_04(self):
        identifier = "ema_declaration_2022_04"
        generated_dict = self.ema_declaration_2022_04._get_declaration()
        self._compare_with_truth_base("ema_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_ema_declaration_2022_05(self):
        identifier = "ema_declaration_2022_05"
        generated_dict = self.ema_declaration_2022_05._get_declaration()
        self._compare_with_truth_base("ema_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_ema_declaration_2022_06(self):
        identifier = "ema_declaration_2022_06"
        generated_dict = self.ema_declaration_2022_06._get_declaration()
        self._compare_with_truth_base("ema_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_ema_declaration_2022_07(self):
        identifier = "ema_declaration_2022_07"
        generated_dict = self.ema_declaration_2022_07._get_declaration()
        self._compare_with_truth_base("ema_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_ema_declaration_2022_08(self):
        identifier = "ema_declaration_2022_08"
        generated_dict = self.ema_declaration_2022_08._get_declaration()
        self._compare_with_truth_base("ema_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_ema_declaration_2022_09(self):
        identifier = "ema_declaration_2022_09"
        generated_dict = self.ema_declaration_2022_09._get_declaration()
        self._compare_with_truth_base("ema_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_ema_declaration_2022_10(self):
        identifier = "ema_declaration_2022_10"
        generated_dict = self.ema_declaration_2022_10._get_declaration()
        self._compare_with_truth_base("ema_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_ema_declaration_2022_11(self):
        identifier = "ema_declaration_2022_11"
        generated_dict = self.ema_declaration_2022_11._get_declaration()
        self._compare_with_truth_base("ema_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_ema_declaration_2022_12(self):
        identifier = "ema_declaration_2022_12"
        generated_dict = self.ema_declaration_2022_12._get_declaration()
        self._compare_with_truth_base("ema_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_ema_declaration_2023_01(self):
        identifier = "ema_declaration_2023_01"
        generated_dict = self.ema_declaration_2023_01._get_declaration()
        self._compare_with_truth_base("ema_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_ema_declaration_2023_02(self):
        identifier = "ema_declaration_2023_02"
        generated_dict = self.ema_declaration_2023_02._get_declaration()
        self._compare_with_truth_base("ema_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_statistic_declaration_2021_11(self):
        identifier = "statistic_declaration_2021_11"
        generated_dict = self.statistic_declaration_2021_11._get_declaration()
        self._compare_with_truth_base("statistic_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_statistic_declaration_2021_12(self):
        identifier = "statistic_declaration_2021_12"
        generated_dict = self.statistic_declaration_2021_12._get_declaration()
        self._compare_with_truth_base("statistic_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_statistic_declaration_2022_01(self):
        identifier = "statistic_declaration_2022_01"
        generated_dict = self.statistic_declaration_2022_01._get_declaration()
        self._compare_with_truth_base("statistic_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_statistic_declaration_2022_02(self):
        identifier = "statistic_declaration_2022_02"
        generated_dict = self.statistic_declaration_2022_02._get_declaration()
        self._compare_with_truth_base("statistic_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_statistic_declaration_2022_03(self):
        identifier = "statistic_declaration_2022_03"
        generated_dict = self.statistic_declaration_2022_03._get_declaration()
        self._compare_with_truth_base("statistic_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_statistic_declaration_2022_04(self):
        identifier = "statistic_declaration_2022_04"
        generated_dict = self.statistic_declaration_2022_04._get_declaration()
        self._compare_with_truth_base("statistic_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_statistic_declaration_2022_05(self):
        identifier = "statistic_declaration_2022_05"
        generated_dict = self.statistic_declaration_2022_05._get_declaration()
        self._compare_with_truth_base("statistic_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_statistic_declaration_2022_06(self):
        identifier = "statistic_declaration_2022_06"
        generated_dict = self.statistic_declaration_2022_06._get_declaration()
        self._compare_with_truth_base("statistic_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_statistic_declaration_2022_07(self):
        identifier = "statistic_declaration_2022_07"
        generated_dict = self.statistic_declaration_2022_07._get_declaration()
        self._compare_with_truth_base("statistic_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_statistic_declaration_2022_08(self):
        identifier = "statistic_declaration_2022_08"
        generated_dict = self.statistic_declaration_2022_08._get_declaration()
        self._compare_with_truth_base("statistic_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_statistic_declaration_2022_09(self):
        identifier = "statistic_declaration_2022_09"
        generated_dict = self.statistic_declaration_2022_09._get_declaration()
        self._compare_with_truth_base("statistic_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_statistic_declaration_2022_10(self):
        identifier = "statistic_declaration_2022_10"
        generated_dict = self.statistic_declaration_2022_10._get_declaration()
        self._compare_with_truth_base("statistic_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_statistic_declaration_2022_11(self):
        identifier = "statistic_declaration_2022_11"
        generated_dict = self.statistic_declaration_2022_11._get_declaration()
        self._compare_with_truth_base("statistic_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_statistic_declaration_2022_12(self):
        identifier = "statistic_declaration_2022_12"
        generated_dict = self.statistic_declaration_2022_12._get_declaration()
        self._compare_with_truth_base("statistic_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_statistic_declaration_2023_01(self):
        identifier = "statistic_declaration_2023_01"
        generated_dict = self.statistic_declaration_2023_01._get_declaration()
        self._compare_with_truth_base("statistic_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_statistic_declaration_2023_02(self):
        identifier = "statistic_declaration_2023_02"
        generated_dict = self.statistic_declaration_2023_02._get_declaration()
        self._compare_with_truth_base("statistic_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_is_declaration_2021_11(self):
        identifier = "is_declaration_2021_11"
        generated_dict = self.is_declaration_2021_11._get_declaration()
        self._compare_with_truth_base("is_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_is_declaration_2021_12(self):
        identifier = "is_declaration_2021_12"
        generated_dict = self.is_declaration_2021_12._get_declaration()
        self._compare_with_truth_base("is_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_is_declaration_2022_01(self):
        identifier = "is_declaration_2022_01"
        generated_dict = self.is_declaration_2022_01._get_declaration()
        self._compare_with_truth_base("is_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_is_declaration_2022_02(self):
        identifier = "is_declaration_2022_02"
        generated_dict = self.is_declaration_2022_02._get_declaration()
        self._compare_with_truth_base("is_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_is_declaration_2022_03(self):
        identifier = "is_declaration_2022_03"
        generated_dict = self.is_declaration_2022_03._get_declaration()
        self._compare_with_truth_base("is_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_is_declaration_2022_04(self):
        identifier = "is_declaration_2022_04"
        generated_dict = self.is_declaration_2022_04._get_declaration()
        self._compare_with_truth_base("is_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_is_declaration_2022_05(self):
        identifier = "is_declaration_2022_05"
        generated_dict = self.is_declaration_2022_05._get_declaration()
        self._compare_with_truth_base("is_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_is_declaration_2022_06(self):
        identifier = "is_declaration_2022_06"
        generated_dict = self.is_declaration_2022_06._get_declaration()
        self._compare_with_truth_base("is_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_is_declaration_2022_07(self):
        identifier = "is_declaration_2022_07"
        generated_dict = self.is_declaration_2022_07._get_declaration()
        self._compare_with_truth_base("is_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_is_declaration_2022_08(self):
        identifier = "is_declaration_2022_08"
        generated_dict = self.is_declaration_2022_08._get_declaration()
        self._compare_with_truth_base("is_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_is_declaration_2022_09(self):
        identifier = "is_declaration_2022_09"
        generated_dict = self.is_declaration_2022_09._get_declaration()
        self._compare_with_truth_base("is_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_is_declaration_2022_10(self):
        identifier = "is_declaration_2022_10"
        generated_dict = self.is_declaration_2022_10._get_declaration()
        self._compare_with_truth_base("is_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_is_declaration_2022_11(self):
        identifier = "is_declaration_2022_11"
        generated_dict = self.is_declaration_2022_11._get_declaration()
        self._compare_with_truth_base("is_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_is_declaration_2022_12(self):
        identifier = "is_declaration_2022_12"
        generated_dict = self.is_declaration_2022_12._get_declaration()
        self._compare_with_truth_base("is_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_is_declaration_2023_01(self):
        identifier = "is_declaration_2023_01"
        generated_dict = self.is_declaration_2023_01._get_declaration()
        self._compare_with_truth_base("is_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_is_declaration_2023_02(self):
        identifier = "is_declaration_2023_02"
        generated_dict = self.is_declaration_2023_02._get_declaration()
        self._compare_with_truth_base("is_declaration", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_rectificate_2022_01(self):
        identifier = "rectificate_2022_01"
        generated_dict = self.rectificate_2022_01._get_declaration()
        self._compare_with_truth_base("rectificate", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_prospective_2023_01(self):
        identifier = "yearly_prospective_2023_01"
        generated_dict = self.yearly_prospective_2023_01._get_declaration()
        self._compare_with_truth_base("yearly_prospective", identifier, generated_dict)

    @freeze_time("2025-12-16")
    def test_lpp_basis_report_with_employee_creation(self):
        """
        Test employee creation for Swiss company while having duplicate LPP reports.
        """
        swiss_company = self.env.company
        lpp_report_1 = self.env['l10n.ch.lpp.basis.report'].create({
            'year': datetime.now().year,
            'month': str(datetime.now().month),
            'company_id': swiss_company.id,
        })
        lpp_report_2 = lpp_report_1.copy()
        employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'company_id': swiss_company.id,
        })
        self.assertTrue(employee.exists())
        self.assertEqual(employee.company_id, swiss_company)
        self.assertEqual(lpp_report_1.year, 2025)
        self.assertEqual(lpp_report_1.month, '12')
        self.assertEqual(lpp_report_2.year, 2025)
        self.assertEqual(lpp_report_2.month, '12')

    @freeze_time("2023-01-01")
    def test_is_declaration_perception_2022_06(self):
        # Load perception commission IS Rates
        rates_to_load = [
            ('BE_PEL', 'BE_PEL.json'),
            ('TI_PEL', 'TI_PEL.json'),
            ('VD_PEL', 'VD_PEL.json'),
        ]
        for xml_id, file_name in rates_to_load:
            rule_parameter = self.env['hr.rule.parameter'].create({
                'name': f'CH Withholding Tax: {xml_id}',
                'code': f'l10n_ch_withholding_tax_rates_{xml_id}',
                'country_id': self.env.ref('base.ch').id,
            })
            self.env['hr.rule.parameter.value'].create({
                'parameter_value': json.load(file_open(f'l10n_ch_hr_payroll_elm_transmission/tests/data/is_rates/{file_name}')),
                'rule_parameter_id': rule_parameter.id,
                'date_from': date(2021, 1, 1),
            })

        identifier = "is_declaration_perception_2022_06"
        self.is_declaration_2022_06.action_prepare_data()
        generated_dict = self.is_declaration_2022_06._get_declaration()
        self._compare_with_truth_base("is_declaration_perception", identifier, generated_dict)
