# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from odoo import Command
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon
from .test_l10n_id_efaktur_coretax import TestEfakturCoretax


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestIndonesianEfakturDownload(TestEfakturCoretax, AccountTestInvoicingHttpCommon):

    # ==========================================
    # Test outcome of downloading files
    # ==========================================

    @freeze_time('2019-05-01')
    def test_efaktur_download_one_document(self):
        """ Test that when downloading the invoice, csv file should be generated in format of
        efaktur_(date)_(time).csv """
        # Create invoice and post
        invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner_a.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_sale_a.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
        })
        invoice.action_post()

        # Download
        action = invoice.download_efaktur()

        # Verify the result of download
        self.authenticate(self.env.user.login, self.env.user.login)
        result = self.url_open(url=action['url'])
        self.assertRegex(result.headers.get('Content-Disposition', ''), r"efaktur_2019-05-01.*.xml")

        # If later on we try to download document for invoice 1 again, it should generate the same file
        document_name = result.headers.get('Content-Disposition')
        action = invoice.download_efaktur()
        result = self.url_open(url=action['url'])
        self.assertEqual(result.headers.get('Content-Disposition', ''), document_name)

    def test_efaktur_download_multiple(self):
        """ Create the 2 documents on 2 separate invoices, then when we run the downlaod from the document side,
        it should generate a zip file instead """
        # Create 2 invoices, then generate document separately for both
        # freeze_time is used when posting invoices to prevent the same timing of efaktur downloade
        # which results to 2 files having the same name
        invoice_1 = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner_a.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_sale_a.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
        })

        with freeze_time("2024-07-01 08:00:00"):
            invoice_1.action_post()
            invoice_1.download_efaktur()

        invoice_2 = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner_a.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_sale_a.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
        })

        with freeze_time("2024-07-01 09:00:00"):
            invoice_2.action_post()
            invoice_2.download_efaktur()

        # There should be total of 2 documents combined among the 2 invoices
        invoices = invoice_1 + invoice_2
        self.assertEqual(len(invoices.l10n_id_coretax_document), 2)

        # When downloading just the document, should generate zip file
        action = invoices.l10n_id_coretax_document.action_download()
        self.authenticate(self.env.user.login, self.env.user.login)
        result = self.url_open(url=action['url'])
        self.assertRegex(result.headers.get('Content-Disposition'), r"efaktur.zip")
