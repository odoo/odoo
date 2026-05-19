# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import unquote

from odoo import Command
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon

from .test_l10n_id_ebupot import TestEBupot


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestEBupotDownload(TestEBupot, AccountTestInvoicingHttpCommon):

    # ==========================================
    # Test outcome of downloading files
    # ==========================================

    def test_ebupot_download_one_document(self):
        """ Test that when downloading the payment, csv file should be generated in format of
        (partner)_(payment_month)_ebupot_(index).csv """

        payment1 = self._create_valid_payment()
        bill1 = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'ref': 'ABC123',
            'invoice_date': payment1.date,
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'line',
                'quantity': 1,
                'price_unit': 1000,
                'tax_ids': [self.tax_pph_22.id],
            })],
        })
        bill1.action_post()
        payment1.action_post()
        bill1.reconciled_payment_ids = payment1
        payment1.reconciled_bill_ids = bill1

        # Download
        action = payment1.download_ebupot()

        # Verify the result of download
        self.authenticate(self.env.user.login, self.env.user.login)
        result = self.url_open(url=action['url'])
        self.assertRegex(
            unquote(result.headers['Content-Disposition'].split("filename*=UTF-8''")[-1]),
            r"ebupot_.*\.xml"
        )
