# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase, tagged
import os

directory = os.path.dirname(__file__)


@tagged('post_install', '-at_install')
class TestCaseIndexation(TransactionCase):

    def test_attachment_pdf_indexation(self):
        with open(os.path.join(directory, 'files', 'test_content.pdf'), 'rb') as file:
            pdf = file.read()
            text = self.env['ir.attachment']._index(pdf, 'application/pdf')
            self.assertEqual(text, 'TestContent!!\x0c', 'the index content should be correct')
