from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountBankStatementImport(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('cz')
    def setUpClass(cls):
        super().setUpClass()

    def test_cz_bank_transaction_with_variable_symbol(self):
        """Ensure the variable symbol is prepended to the payment reference when available."""

        bsl_with_vs, bsl_with_details = self.env['account.bank.statement.line'].with_context(
            skip_statement_line_cron_trigger=True,
        ).create([
            {
                'online_transaction_identifier': 'transaction_1',
                'date': '2026-08-07',
                'payment_ref': 'Office rent',
                'l10n_cz_variable_symbol': '202600111',
                'amount': 10.0,
            },
            {
                'online_transaction_identifier': 'transaction_2',
                'date': '2026-08-07',
                'payment_ref': 'Last Year Interests',
                'amount': 12.0,
                'transaction_details': {
                    'amount': 12.0,
                    'partner_name': 'ABC',
                    'extra': {
                        'variable_code': '202600222',
                    },
                },
            },
        ])

        self.assertEqual(bsl_with_vs.payment_ref, '202600111 - Office rent')
        self.assertEqual(bsl_with_details.payment_ref, '202600222 - Last Year Interests')
