# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEt(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template('et')
    def setUpClass(cls):
        super().setUpClass()

    def test_default_expense_account(self):
        product = self.env['product.product'].create({'name': 'Product'})
        bill = self.init_invoice('in_invoice', products=product, post=True)
        self.assertEqual(bill.invoice_line_ids.account_id, self.env['account.chart.template'].ref('l10n_et5111'))
        self.assertEqual(bill.invoice_line_ids.account_id.account_type, 'expense')
