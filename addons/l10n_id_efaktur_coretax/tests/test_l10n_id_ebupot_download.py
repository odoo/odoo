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

    # def test_ebupot_download_multiple(self):
    #     """ Create the 2 documents on 2 separate payments, then when we run the downlaod from the document side,
    #     it should generate a zip file instead """
    #     payment1 = self._create_valid_payment()
    #     payment2 = self._create_valid_payment()

    #     # Different partner
    #     partner_b = self.env['res.partner'].create({
    #         'name': 'Partner B',
    #         'vat': '9999999999999999',
    #         'country_id': self.env.ref('base.id').id,
    #     })

    #     payment2.partner_id = partner_b
    #     payment2.date = '2026-05-01'  # different month

    #     bill1 = self.env['account.move'].create({
    #         'move_type': 'in_invoice',
    #         'invoice_date': payment1.date,
    #         'partner_id': self.partner_a.id,
    #         'invoice_line_ids': [Command.create({
    #             'name': 'line',
    #             'quantity': 1,
    #             'price_unit': 1000,
    #             'tax_ids': [self.tax_pph_22.id],
    #         })],
    #     })

    #     bill2 = self.env['account.move'].create({
    #         'move_type': 'in_invoice',
    #         'invoice_date': payment2.date,
    #         'partner_id': partner_b.id,
    #         'invoice_line_ids': [Command.create({
    #             'name': 'line',
    #             'quantity': 1,
    #             'price_unit': 1000,
    #             'tax_ids': [self.tax_pph_22.id],
    #         })],
    #     })

    #     bill1.action_post()
    #     bill2.action_post()
    #     payment1.action_post()
    #     payment2.action_post()

    #     bill1.reconciled_payment_ids = payment1
    #     payment1.reconciled_bill_ids = bill1
    #     bill2.reconciled_payment_ids = payment2
    #     payment2.reconciled_bill_ids = bill2

    #     result = (payment1 | payment2).download_ebupot()
    #     # There should be total of 2 documents combined among the 2 invoices
    #     payments = payment1 + payment2
    #     self.assertEqual(len(payments.l10n_id_ebupot_document_xml.attachment_ids), 2)

    #     # When downloading just the document, should generate zip file
    #     action = payments.l10n_id_ebupot_document_xml.action_download()
    #     self.authenticate(self.env.user.login, self.env.user.login)
    #     result = self.url_open(url=action['url'])
    #     self.assertRegex(result.headers.get('Content-Disposition'), r"ebupot.zip")
