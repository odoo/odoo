from io import BytesIO
from zipfile import ZipFile

from odoo.fields import Command
from odoo.tests.common import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


@tagged('post_install', '-at_install')
class TestDownloadDocs(AccountTestInvoicingHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a.country_id = cls.env.ref('base.be')
        cls.partner_a.invoice_edi_format = 'ubl_bis3'
        invoice_1 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'price_unit': 100,
                    'product_id': cls.product_a.id,
                    'tax_ids': cls.tax_sale_a.ids,
                })
            ]
        })
        invoice_2 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'price_unit': 20,
                    'product_id': cls.product_a.id,
                    'tax_ids': cls.tax_sale_a.ids,
                })
            ]
        })
        invoice_3 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'price_unit': 300,
                    'product_id': cls.product_a.id,
                    'tax_ids': cls.tax_sale_a.ids,
                })
            ]
        })
        cls.invoices = invoice_1 + invoice_2
        cls.invoices.action_post()
        cls.invoices._generate_and_send(sending_methods=['manual'])
        cls.invoices += invoice_3
        assert invoice_1.invoice_pdf_report_id and invoice_2.invoice_pdf_report_id and not invoice_3.invoice_pdf_report_id
        assert invoice_1.ubl_cii_xml_id and invoice_2.ubl_cii_xml_id and not invoice_3.ubl_cii_xml_id

    def test_download_invoice_documents_filetype_all(self):
        self.authenticate(self.env.user.login, self.env.user.login)
        url = f'/account/download_invoice_documents/{",".join(map(str, self.invoices.ids))}/all'
        res = self.url_open(url)
        self.assertEqual(res.status_code, 200)
        with ZipFile(BytesIO(res.content)) as zip_file:
            files = zip_file.namelist()
            self.assertEqual(len(files), 5)
            xml_files = sum(file.endswith('.xml') for file in files)
            self.assertEqual(xml_files, 2)
