# -*- coding: utf-8 -*-

from pathlib import Path
from unittest import skipIf

from odoo.tests.common import TransactionCase, tagged
from odoo.tools.misc import file_open

directory = Path(__file__).parent

try:
    from pdfminer.pdfinterp import PDFResourceManager
except ImportError:
    PDFResourceManager = None


@tagged('post_install', '-at_install')
class TestCaseIndexation(TransactionCase):

    @skipIf(PDFResourceManager is None, "pdfminer not installed")
    def test_attachment_pdf_indexation(self):
        with file_open(str(directory / 'files' / 'test_content.pdf'), 'rb') as file:
            pdf = file.read()
            text = self.env['ir.attachment']._index(pdf, 'application/pdf')
            self.assertEqual(text, 'TestContent!!', 'the index content should be correct')
