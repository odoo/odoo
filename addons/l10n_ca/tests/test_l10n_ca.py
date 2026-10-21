# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nCa(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('ca')
    def setUpClass(cls):
        super().setUpClass()

    def test_currency_exchange_accounts(self):
        company = self.env.company
        ChartTemplate = self.env['account.chart.template']
        self.assertEqual(company.income_currency_exchange_account_id, ChartTemplate.ref('l10n_ca_612100'))
        self.assertEqual(company.expense_currency_exchange_account_id, ChartTemplate.ref('l10n_ca_612200'))
