# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestNpAccountMove(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('np')
    def setUpClass(cls):
        super().setUpClass()

    def test_compute_fiscal_date_invoice(self):
        invoice = self._create_invoice(invoice_date='2024-08-01')
        self.assertEqual(invoice.l10n_np_fiscal_date, '04/17/2081')
        self.assertEqual(invoice._l10n_np_format_date('2024-08-10'), '04/26/2081')
        self.assertEqual(invoice._l10n_np_format_date('2024-08-05'), '04/21/2081')

    def test_compute_fiscal_date_journal_entry(self):
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2024-08-01',
        })
        self.assertEqual(move.l10n_np_fiscal_date, '04/17/2081')

    def test_compute_fiscal_date_out_of_range(self):
        invoice = self._create_invoice(invoice_date='2040-01-01')
        self.assertEqual(invoice.l10n_np_fiscal_date, '')
        self.assertEqual(invoice._l10n_np_format_date(False), '')
