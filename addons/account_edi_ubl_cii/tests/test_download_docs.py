from io import BytesIO
from zipfile import ZipFile
from lxml import etree

from odoo.fields import Command
from odoo.tests.common import tagged
from odoo.addons.account_edi_ubl_cii.tests.common import TestUblBis3Common, TestUblCiiBECommon
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


@tagged('post_install', '-at_install')
class TestDownloadDocs(TestUblBis3Common, TestUblCiiBECommon, AccountTestInvoicingHttpCommon):

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        invoice_1 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_be.id,
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
            'partner_id': cls.partner_be.id,
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
            'partner_id': cls.partner_be.id,
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
        cls._generate_invoice_ubl_file(cls.invoices)
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

    def test_download_ubl_customer_without_endpoint(self):
        """ The UBL download must not be blocked by the export errors (e.g. IBR-080 when the customer
        has no electronic address): the downloaded XML is only an export, never stored on the invoice,
        as for multiple invoices.
        """
        partner = self.env['res.partner'].create({
            **self._create_partner_default_values(),
            'name': "partner without endpoint",
            'country_id': self.env.ref('base.be').id,
        })
        invoice = self._create_invoice_one_line(
            price_unit=100,
            product_id=self.product_a,
            tax_ids=self.tax_sale_a,
            partner_id=partner,
            post=True,
        )
        self.assertFalse(partner.routing_identifier)

        # The errors are still computed...
        docs_data = invoice._get_invoice_legal_documents('ubl', allow_fallback=True)
        self.assertTrue(docs_data[0].get('errors'))

        # ...but don't block the download.
        self.authenticate(self.env.user.login, self.env.user.login)
        res = self.url_open(f'/account/download_invoice_documents/{invoice.id}/ubl?allow_fallback=true')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers['Content-Type'], 'xml')
        xml_tree = etree.fromstring(res.content)
        self.assertIsNotNone(xml_tree.find('{*}AccountingCustomerParty/{*}Party'))
        self.assertIsNone(xml_tree.find('{*}AccountingCustomerParty/{*}Party/{*}EndpointID'))
        self.assertFalse(invoice.ubl_cii_xml_id)
