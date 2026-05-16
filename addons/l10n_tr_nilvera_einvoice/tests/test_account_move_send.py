from odoo.tests import tagged
from .test_xml_ubl_tr_common import TestUBLTRCommon
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
import xml.etree.ElementTree as ET


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestTRAccountMoveSend(TestAccountMoveSendCommon, TestUBLTRCommon):

    @classmethod
    @TestAccountMoveSendCommon.setup_country('tr')
    def setUpClass(cls):
        super().setUpClass()
        # ==== Partners ====
        cls.partner_tr = cls.env['res.partner'].create({
            'name': 'partner_tr',
            'invoice_edi_format': 'ubl_tr',
            'l10n_tr_nilvera_customer_status': 'earchive',
        })

    def test_invoice_names_valid_for_nilvera(self):
        valid_names = [
            'INV-2025-00001',
            'R01/2025/00001',
            '123/2025/00001',
            'res.2025.00001',
            'RES2025/00001',
        ]
        invoices = self.env['account.move']
        for name in valid_names:
            invoice = self.init_invoice('out_invoice', invoice_date='2025-11-28', amounts=[1000])
            invoice.name = name
            invoice.action_post()
            invoices |= invoice

        wizard = self.create_send_and_print(invoices)
        self.assertNotIn('tr_moves_with_invalid_name', wizard.alerts)

    def test_invoice_names_invalid_for_nilvera(self):
        invalid_names = [
            'INV/2025/0',
            'INV/25/1012',
            'RESXYZ00001',
            'res2025ABCDE',
            'RES-XYZ-00001',
            'INVOICE/2025/00010',
        ]
        for name in invalid_names:
            invoice = self.init_invoice('out_invoice', invoice_date='2025-11-28', amounts=[1000])
            invoice.name = name
            invoice.action_post()

            wizard = self.create_send_and_print(invoice)
            self.assertIn('tr_moves_with_invalid_name', wizard.alerts)

    def test_no_attachment_on_ubl_xml_for_ubl_tr(self):
        # Setup invoice
        invoice = self.init_invoice(
            move_type='out_invoice',
            partner=self.partner_tr,
            invoice_date='2025-11-28',
            amounts=[1000],
            taxes=self.tax_sale_a,
            post=True,
        )

        # Execute send
        wizard = self.create_send_and_print(invoice, True)
        wizard.sending_methods = False
        wizard.extra_edis = False
        wizard.alerts = False
        wizard.action_send_and_print()

        xml_data = invoice.ubl_cii_xml_id.raw
        self.assertIsNotNone(xml_data, "XML data should exist")

        xml_tree = ET.fromstring(xml_data.decode('utf-8'))

        ns = {'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2'}

        # Main assertion - no attachments should exist
        attachments = xml_tree.findall('.//cac:AdditionalDocumentReference/cac:Attachment', ns)
        self.assertFalse(
            attachments,
            f"Found {len(attachments)} unexpected Attachment node(s) in UBL TR XML"
        )

    def test_send_email_with_recipient_bank(self):
        """
        invoice xml generation should work when company has bank account with bank information
        in order to send email with invoice xml to recipient's bank
        """
        bank = self.env['res.bank'].create({
            'name': 'Test Bank',
            'bic': 'TESTTRISXXX',
        })
        self.company_data['company'].bank_ids.bank_id = bank.id

        self.assertTrue(self._generate_invoice_xml(self.einvoice_partner), "XML generation failed")
