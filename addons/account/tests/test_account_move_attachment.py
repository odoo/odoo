from base64 import b64decode
from os.path import basename

from lxml import etree

from odoo import Command
from odoo.tests import HttpCase, tagged
from odoo.tools import BinaryBytes, file_open

from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


@tagged("-at_install", "post_install")
class TestAccountMoveAttachment(HttpCase):

    def test_preserving_manually_added_attachments(self):
        """ Preserve attachments manually added (not coming from emails) to an invoice """
        self.authenticate("admin", "admin")

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
        })
        self.assertFalse(invoice.attachment_ids)
        response = self.url_open("/mail/attachment/upload",
            {
                "csrf_token": self.csrf_token(),
                "thread_id": invoice.id,
                "thread_model": "account.move",
            },
            files={'ufile': ('salut.txt', b"Salut !\n", 'text/plain')},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(invoice.attachment_ids)

    def test_create_records_from_empty_pdf_attachment(self):
        """Ensure importing an empty PDF attachment does not crash and still returns created records."""
        attachment = self.env['ir.attachment'].create({
            'name': 'invoice.pdf',
            'mimetype': 'application/pdf',
        })
        records = self.env['account.move']._create_records_from_attachments(attachment)
        self.assertTrue(records)


@tagged("-at_install", "post_install")
class TestAccountMoveAttachmentImport(AccountTestInvoicingHttpCommon):

    def _send_account_move(self, account_move):
        account_move.write({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-21',
            'date': '2019-01-21',
            'invoice_line_ids': [
                Command.create({'name': 'test line', 'product_id': self.product_a.id}),
            ],
        })
        account_move.action_post()
        account_move.action_send_and_print()

    def test_check_create_from_pdf_match(self):
        """Creating records from a PDF uses that PDF as the main document for Send & Print."""
        pdf_path = 'account/tests/test_files/test_pdf.pdf'
        with file_open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()

        attachment = self.env['ir.attachment'].create({
            'name': basename(pdf_path),
            'mimetype': 'application/pdf',
            'raw': BinaryBytes(pdf_bytes),
        })
        account_move = self.env['account.move']._create_records_from_attachments(attachment)
        self._send_account_move(account_move)

        self.assertEqual(pdf_bytes, account_move.invoice_pdf_report_id.raw.content)

    def test_check_create_from_xml_match(self):
        """Creating records from an XML with embedded PDF uses that PDF as the main document for Send & Print."""
        xml_path = 'account/tests/test_files/xml_with_embedded_pdf.xml'
        with file_open(xml_path, 'rb') as f:
            xml_bytes = f.read()

        attachment = self.env['ir.attachment'].create({
            'name': basename(xml_path),
            'mimetype': 'application/xml',
            'raw': BinaryBytes(xml_bytes),
        })
        account_move = self.env['account.move']._create_records_from_attachments(attachment)
        self._send_account_move(account_move)

        xml_root = etree.fromstring(xml_bytes)
        [doc] = xml_root.xpath("//*[contains(local-name(), 'EmbeddedDocumentBinaryObject')]")
        embedded_pdf = b64decode(doc.text)

        self.assertEqual(embedded_pdf, account_move.invoice_pdf_report_id.raw.content)
