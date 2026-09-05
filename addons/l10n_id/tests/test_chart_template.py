# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestIdChartTemplate(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('id')
    @AccountTestInvoicingCommon.setup_chart_template('id')
    def setUpClass(cls):
        super().setUpClass()

    def test_no_duplicate_utility_accounts(self):
        """ Test that loading the Indonesian chart must not create duplicate utility accounts. """
        Account = self.env['account.account']
        company = self.company_data['company']
        ChartTemplate = self.env['account.chart.template'].with_company(company)

        for account_name in ('Outstanding Receipts', 'Outstanding Payments', 'Funds in Transit'):
            accounts = Account.search([
                ('company_ids', 'in', company.id),
                ('name', '=', account_name),
            ])
            self.assertEqual(
                len(accounts),
                1,
                f"Expected a single '{account_name}' account, found {accounts.mapped('code')}",
            )

        outstanding_receipts = ChartTemplate.ref('account_journal_payment_debit_account_id')
        outstanding_payments = ChartTemplate.ref('account_journal_payment_credit_account_id')
        self.assertEqual(outstanding_receipts.code, '11120002')
        self.assertEqual(outstanding_payments.code, '11120003')
        self.assertEqual(company.transfer_account_id.code, '19999991')
        self.assertTrue(company.transfer_account_id.reconcile)
        self.assertEqual(company.transfer_account_id, ChartTemplate.ref('l10n_id_19999991'))
