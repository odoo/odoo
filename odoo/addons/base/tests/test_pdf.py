# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.tools import pdf
from odoo.modules.module import get_module_resource
import io
import pikepdf


class TestPdf(TransactionCase):
    """ Tests on pdf. """

    def setUp(self):
        super().setUp()
        file_path = get_module_resource('base', 'tests', 'minimal.pdf')
        self.file = open(file_path, 'rb').read()
        self.minimal_reader_buffer = io.BytesIO(self.file)

    def test_odoo_pdf_file_reader(self):
        with pdf.OdooPdf.open(self.minimal_reader_buffer) as minimal_pdf:
            attachments = list(minimal_pdf.get_attachments())
            self.assertEqual(len(attachments), 0)

            minimal_pdf.add_attachment('test_attachment.txt', b'My awesome attachment')

            attachments = list(minimal_pdf.get_attachments())
            self.assertEqual(len(attachments), 1)

    def test_odoo_pdf_file_writer(self):
        with pdf.OdooPdf.open(self.minimal_reader_buffer) as minimal_pdf:
            attachments = list(minimal_pdf.get_attachments())
            self.assertEqual(len(attachments), 0)

            minimal_pdf.add_attachment('test_attachment.txt', b'My awesome attachment')
            attachments = list(minimal_pdf.get_attachments())
            self.assertEqual(len(attachments), 1)

            minimal_pdf.add_attachment('another_attachment.txt', b'My awesome OTHER attachment')
            attachments = list(minimal_pdf.get_attachments())
            self.assertEqual(len(attachments), 2)

    def test_odoo_pdf_file_reader_with_owner_encryption(self):
        with pdf.OdooPdf.open(self.minimal_reader_buffer) as minimal_pdf, io.BytesIO() as _buffer:
            minimal_pdf.add_attachment('test_attachment.txt', b'My awesome attachment')
            minimal_pdf.add_attachment('another_attachment.txt', b'My awesome OTHER attachment')

            minimal_pdf.save(_buffer, encryption=pikepdf.Encryption(user="", owner="foo"))

            with pdf.OdooPdf.open(_buffer) as encrypted_pdf:
                attachments = list(encrypted_pdf.get_attachments())
                self.assertEqual(len(attachments), 2)

    def test_merge_pdf(self):
        with pdf.OdooPdf.open(self.minimal_reader_buffer) as minimal_pdf:
            self.assertEqual(len(minimal_pdf.pages), 1)

        merged_file = pdf.merge_pdf([self.file, self.file])
        with pdf.OdooPdf.open(io.BytesIO(merged_file)) as merged_pdf:
            self.assertEqual(len(merged_pdf.pages), 2)

    def test_branded_file_writer(self):
        with pdf.OdooPdf.open(self.minimal_reader_buffer) as minimal_pdf, io.BytesIO() as _buffer:
            minimal_pdf.save(_buffer)

            # Read the metadata of the newly created pdf.
            with pdf.OdooPdf.open(_buffer) as branded_pdf:
                with branded_pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
                    self.assertEqual(meta['xmp:CreatorTool'], 'Odoo')
                    self.assertEqual(meta['pdf:Producer'], "Odoo")

    def tearDown(self):
        super().tearDown()
        self.minimal_reader_buffer.close()
