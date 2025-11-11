from unittest import skipIf

from odoo.tests.common import TransactionCase, tagged

try:
    from pdfminer.pdfinterp import PDFResourceManager
except ImportError:
    PDFResourceManager = None


@tagged('post_install', '-at_install')
class TestCaseIndexation(TransactionCase):

    @skipIf(PDFResourceManager is None, "pdfminer not installed")
    def test_attachment_pdf_indexation(self):
        pdf = self.read_file_contents('attachment_indexation/tests/files/test_content.pdf')
        text = self.env['ir.attachment']._index(pdf, 'application/pdf')
        self.assertEqual(text, 'TestContent!!', 'the index content should be correct')
