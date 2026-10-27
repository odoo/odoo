# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nGrFiscalPosition(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('gr')
    def setUpClass(cls):
        super().setUpClass()

    def test_fiscal_positions_without_mapping_keep_taxes(self):
        """ The domestic and Private Intra-Community positions keep every tax, inactive ones included. """
        taxes = self.env['account.tax'].with_context(active_test=False).search(
            self.env['account.tax']._check_company_domain(self.env.company),
        )
        taxes.active = True
        for xmlid in ('fiscal_position_template_domestic', 'fiscal_position_template_4'):
            fiscal_position = self.env['account.chart.template'].ref(xmlid)
            for tax in taxes:
                with self.subTest(fiscal_position=fiscal_position.name, tax=tax.name):
                    self.assertEqual(fiscal_position.map_tax(tax), tax)
