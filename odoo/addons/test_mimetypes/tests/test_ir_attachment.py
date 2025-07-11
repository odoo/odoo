from odoo.tests.common import TransactionCase
from odoo.tools.misc import file_open


class TestIrAttachmentMimeGuessing(TransactionCase):
    def create_ir_attachment(self, extension):
        filename = f'case.{extension}'
        path = f'test_mimetypes/tests/testfiles/{filename}'
        with file_open(path, 'rb') as f:
            f.filename = filename
            attachment = self.env['ir.attachment']._from_request_file(
                f,
                mimetype='GUESS',
            )
            return attachment

    def test_ir_attachment_xls(self):
        attachment = self.create_ir_attachment('xls')
        self.assertEqual(
            attachment.mimetype,
            'application/vnd.ms-excel'
        )

    def test_ir_attachment_xlsx(self):
        attachment = self.create_ir_attachment('xlsx')
        self.assertEqual(
            attachment.mimetype,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    def test_ir_attachment_docx(self):
        attachment = self.create_ir_attachment('docx')
        self.assertEqual(
            attachment.mimetype,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    def test_ir_attachment_odt(self):
        attachment = self.create_ir_attachment('odt')
        self.assertEqual(
            attachment.mimetype,
            'application/vnd.oasis.opendocument.text'
        )

    def test_ir_attachment_ods(self):
        attachment = self.create_ir_attachment('ods')
        self.assertEqual(
            attachment.mimetype,
            'application/vnd.oasis.opendocument.spreadsheet'
        )
