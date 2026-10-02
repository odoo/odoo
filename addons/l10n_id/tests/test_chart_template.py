from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nIdChartTemplate(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template('id')
    def setUpClass(cls):
        super().setUpClass()

    def test_bank_journal_default_account(self):
        bank_journal = self.company_data['default_journal_bank']
        self.assertRecordValues(bank_journal.default_account_id, [{'code': '11120004', 'account_type': 'asset_cash'}])
