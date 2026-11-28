from unittest.mock import patch

from odoo.tests import tagged, HttpCase


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

    def test_is_xml_content_relevant_edi_document(self):
        """XML files recognized by the import (e.g. UBL or CII invoices) are worth reading when not indexed."""
        attachment = self.env['ir.attachment'].create({
            'name': 'invoice.xml',
            'raw': b'<?xml version="1.0" encoding="UTF-8"?><Invoice><ID>INV/2026/00042</ID></Invoice>',
            'mimetype': 'application/xml',
        })
        self.assertFalse(attachment.index_content)

        # the formats are recognized by other modules (e.g. account_edi_ubl_cii)
        with patch.object(
            self.registry['account.move'], '_get_import_file_type', return_value='test.xml.format',
        ) as mock_type:
            self.assertTrue(attachment._is_xml_content_relevant())
        self.assertEqual(mock_type.call_args.args[0]['xml_tree'].findtext('ID'), 'INV/2026/00042')

    def test_is_xml_content_relevant_other_files(self):
        """Only electronic documents recognized by the import are worth reading when not indexed."""
        xml_attachment, zip_attachment = self.env['ir.attachment'].create([{
            'name': 'config.xml',
            'raw': b'<?xml version="1.0" encoding="UTF-8"?><config><Attachment>not an invoice</Attachment></config>',
            'mimetype': 'application/xml',
        }, {
            'name': 'archive.zip',
            'raw': b'PK\x05\x06' + b'\x00' * 18,
            'mimetype': 'application/zip',
        }])
        self.assertEqual(xml_attachment.mimetype, 'application/xml')
        self.assertFalse(xml_attachment.index_content)
        self.assertFalse(xml_attachment._is_xml_content_relevant())

        # the content of other files is not read
        with patch.object(self.registry['account.move'], '_to_files_data') as mock_to_files_data:
            self.assertFalse(zip_attachment._is_xml_content_relevant())
        mock_to_files_data.assert_not_called()
