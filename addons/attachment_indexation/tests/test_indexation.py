from unittest import skipIf

from odoo.tests.common import TransactionCase, tagged
from odoo.tools import file_open

try:
    from pdfminer.pdfinterp import PDFResourceManager
except ImportError:
    PDFResourceManager = None


@tagged('post_install', '-at_install')
class TestCaseIndexation(TransactionCase):

    @skipIf(PDFResourceManager is None, "pdfminer not installed")
    def test_attachment_pdf_indexation(self):
        pdf = self.file_read('attachment_indexation/tests/files/test_content.pdf')
        text = self.env['ir.attachment']._index(pdf, 'application/pdf')
        self.assertEqual(text, 'TestContent!!', 'the index content should be correct')

    @skipIf(PDFResourceManager is None, "pdfminer not installed")
    def test_file_upload_indexation(self):
        test_file = 'attachment_indexation/tests/files/test_content.pdf'
        with file_open(test_file, 'rb') as f:
            attach = self.env['ir.attachment']._upload_file(
                f,
                {'name': 'test_content.pdf'},
            )
        self.assertEqual(attach.index_content, 'TestContent!!')
