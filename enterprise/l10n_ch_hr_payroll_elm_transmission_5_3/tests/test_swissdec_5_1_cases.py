# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.l10n_ch_hr_payroll_elm_transmission_5_3.tests.swissdec_minor_5_1_common import TestSwissdecCommon
from odoo.tests.common import tagged
from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install', 'swissdec_payroll')
class TestSwissdecTestCases(TestSwissdecCommon):
    @freeze_time("2024-01-01")
    def test_yearly_retrospective_5_1_2022_01(self):
        identifier = "yearly_retrospective_5_1_2022_01"
        generated_dict = self.yearly_retrospective_5_1_2022_01._get_declaration()
        self._compare_with_truth_base("yearly_retrospective_5_1", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_5_1_2022_02(self):
        identifier = "yearly_retrospective_5_1_2022_02"
        generated_dict = self.yearly_retrospective_5_1_2022_02._get_declaration()
        self._compare_with_truth_base("yearly_retrospective_5_1", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_5_1_2022_03(self):
        identifier = "yearly_retrospective_5_1_2022_03"
        generated_dict = self.yearly_retrospective_5_1_2022_03._get_declaration()
        self._compare_with_truth_base("yearly_retrospective_5_1", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_5_1_2022_04(self):
        identifier = "yearly_retrospective_5_1_2022_04"
        generated_dict = self.yearly_retrospective_5_1_2022_04._get_declaration()
        self._compare_with_truth_base("yearly_retrospective_5_1", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_5_1_2022_05(self):
        identifier = "yearly_retrospective_5_1_2022_05"
        generated_dict = self.yearly_retrospective_5_1_2022_05._get_declaration()
        self._compare_with_truth_base("yearly_retrospective_5_1", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_5_1_2022_06(self):
        identifier = "yearly_retrospective_5_1_2022_06"
        generated_dict = self.yearly_retrospective_5_1_2022_06._get_declaration()
        self._compare_with_truth_base("yearly_retrospective_5_1", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_5_1_2022_07(self):
        identifier = "yearly_retrospective_5_1_2022_07"
        generated_dict = self.yearly_retrospective_5_1_2022_07._get_declaration()
        self._compare_with_truth_base("yearly_retrospective_5_1", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_5_1_2022_08(self):
        identifier = "yearly_retrospective_5_1_2022_08"
        generated_dict = self.yearly_retrospective_5_1_2022_08._get_declaration()
        self._compare_with_truth_base("yearly_retrospective_5_1", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_5_1_2022_09(self):
        identifier = "yearly_retrospective_5_1_2022_09"
        generated_dict = self.yearly_retrospective_5_1_2022_09._get_declaration()
        self._compare_with_truth_base("yearly_retrospective_5_1", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_5_1_2022_10(self):
        identifier = "yearly_retrospective_5_1_2022_10"
        generated_dict = self.yearly_retrospective_5_1_2022_10._get_declaration()
        self._compare_with_truth_base("yearly_retrospective_5_1", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_5_1_2022_11(self):
        identifier = "yearly_retrospective_5_1_2022_11"
        generated_dict = self.yearly_retrospective_5_1_2022_11._get_declaration()
        self._compare_with_truth_base("yearly_retrospective_5_1", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_5_1_2022_12(self):
        identifier = "yearly_retrospective_5_1_2022_12"
        generated_dict = self.yearly_retrospective_5_1_2022_12._get_declaration()
        self._compare_with_truth_base("yearly_retrospective_5_1", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_5_1_2023_01(self):
        identifier = "yearly_retrospective_5_1_2023_01"
        generated_dict = self.yearly_retrospective_5_1_2023_01._get_declaration()
        self._compare_with_truth_base("yearly_retrospective_5_1", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_5_1_2023_02(self):
        identifier = "yearly_retrospective_5_1_2023_02"
        generated_dict = self.yearly_retrospective_5_1_2023_02._get_declaration()
        self._compare_with_truth_base("yearly_retrospective_5_1", identifier, generated_dict)

