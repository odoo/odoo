# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.l10n_ch_hr_payroll_elm_transmission_5_3.tests.swissdec_minor_5_3_common import TestSwissdecCommon
from odoo.tests.common import tagged
from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install', 'swissdec_payroll')
class TestSwissdecTestCases(TestSwissdecCommon):
    @freeze_time("2024-01-01")
    def test_yearly_retrospective_5_3_2022_11(self):
        identifier = "yearly_retrospective_5_3_2022_11"
        generated_dict = self.yearly_retrospective_5_3_2022_11._get_declaration()
        self._compare_with_truth_base("yearly_retrospective_5_3", identifier, generated_dict)

    @freeze_time("2024-01-01")
    def test_yearly_retrospective_5_3_2022_12(self):
        identifier = "yearly_retrospective_5_3_2022_12"
        generated_dict = self.yearly_retrospective_5_3_2022_12._get_declaration()
        self._compare_with_truth_base("yearly_retrospective_5_3", identifier, generated_dict)
