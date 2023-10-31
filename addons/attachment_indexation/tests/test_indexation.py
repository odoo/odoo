# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase, tagged
from unittest import skipIf
import os

directory = os.path.dirname(__file__)

try:
    from pdfminer.pdfinterp import PDFResourceManager
except ImportError:
    PDFResourceManager = None


@tagged('post_install', '-at_install')
class TestCaseIndexation(TransactionCase):

    @skipIf(PDFResourceManager is None, "pdfminer not installed")
    def test_attachment_pdf_indexation(self):
        with open(os.path.join(directory, 'files', 'test_content.pdf'), 'rb') as file:
            pdf = file.read()
            text = self.env['ir.attachment']._index(pdf, 'application/pdf')
            self.assertEqual(text, 'TestContent!!\x0c', 'the index content should be correct')
