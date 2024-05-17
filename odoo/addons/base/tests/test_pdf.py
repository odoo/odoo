# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.tools import pdf
from odoo.tools.misc import file_open
from odoo.tools.pdf import reshape_text
import io


class TestPdf(TransactionCase):
    """ Tests on pdf. """

    def setUp(self):
        super().setUp()
        self.file = file_open('base/tests/minimal.pdf', 'rb').read()
        self.minimal_reader_buffer = io.BytesIO(self.file)
        self.minimal_pdf_reader = pdf.OdooPdfFileReader(self.minimal_reader_buffer)

    def test_odoo_pdf_file_reader(self):
        attachments = list(self.minimal_pdf_reader.getAttachments())
        self.assertEqual(len(attachments), 0)

        pdf_writer = pdf.PdfFileWriter()
        pdf_writer.cloneReaderDocumentRoot(self.minimal_pdf_reader)
        pdf_writer.addAttachment('test_attachment.txt', b'My awesome attachment')

        attachments = list(self.minimal_pdf_reader.getAttachments())
        self.assertEqual(len(attachments), 1)

    def test_odoo_pdf_file_writer(self):
        attachments = list(self.minimal_pdf_reader.getAttachments())
        self.assertEqual(len(attachments), 0)

        pdf_writer = pdf.OdooPdfFileWriter()
        pdf_writer.cloneReaderDocumentRoot(self.minimal_pdf_reader)

        pdf_writer.addAttachment('test_attachment.txt', b'My awesome attachment')
        attachments = list(self.minimal_pdf_reader.getAttachments())
        self.assertEqual(len(attachments), 1)

        pdf_writer.addAttachment('another_attachment.txt', b'My awesome OTHER attachment')
        attachments = list(self.minimal_pdf_reader.getAttachments())
        self.assertEqual(len(attachments), 2)

    def test_odoo_pdf_file_reader_with_owner_encryption(self):
        pdf_writer = pdf.OdooPdfFileWriter()
        pdf_writer.cloneReaderDocumentRoot(self.minimal_pdf_reader)

        pdf_writer.addAttachment('test_attachment.txt', b'My awesome attachment')
        pdf_writer.addAttachment('another_attachment.txt', b'My awesome OTHER attachment')

        pdf_writer.encrypt("", "foo")

        with io.BytesIO() as writer_buffer:
            pdf_writer.write(writer_buffer)
            encrypted_content = writer_buffer.getvalue()

        with io.BytesIO(encrypted_content) as reader_buffer:
            pdf_reader = pdf.OdooPdfFileReader(reader_buffer)
            attachments = list(pdf_reader.getAttachments())

        self.assertEqual(len(attachments), 2)

    def test_merge_pdf(self):
        self.assertEqual(self.minimal_pdf_reader.getNumPages(), 1)
        page = self.minimal_pdf_reader.getPage(0)

        merged_pdf = pdf.merge_pdf([self.file, self.file])
        merged_reader_buffer = io.BytesIO(merged_pdf)
        merged_pdf_reader = pdf.OdooPdfFileReader(merged_reader_buffer)
        self.assertEqual(merged_pdf_reader.getNumPages(), 2)
        merged_reader_buffer.close()

    def test_branded_file_writer(self):
        # It's not easy to create a PDF with PyPDF2, so instead we copy minimal.pdf with our custom pdf writer
        pdf_writer = pdf.PdfFileWriter()  # BrandedFileWriter
        pdf_writer.cloneReaderDocumentRoot(self.minimal_pdf_reader)
        writer_buffer = io.BytesIO()
        pdf_writer.write(writer_buffer)
        branded_content = writer_buffer.getvalue()
        writer_buffer.close()

        # Read the metadata of the newly created pdf.
        reader_buffer = io.BytesIO(branded_content)
        pdf_reader = pdf.PdfFileReader(reader_buffer)
        pdf_info = pdf_reader.getDocumentInfo()
        self.assertEqual(pdf_info['/Producer'], 'Odoo')
        self.assertEqual(pdf_info['/Creator'], 'Odoo')
        reader_buffer.close()

    def tearDown(self):
        super().tearDown()
        self.minimal_reader_buffer.close()

    def test_reshaping_non_arabic_text(self):
        """
        Test that reshaper doesn't alter non-Arabic text.
        """
        english_text = "Hello, I'm just an English text"
        processed_text = reshape_text(english_text)
        self.assertEqual(english_text, processed_text, "English text shouldn't be altered.")

        brazilian_text = "Ayrton Senna foi o melhor piloto de Formula 1 que já existiu"
        processed_brazilian_text = reshape_text(brazilian_text)
        self.assertEqual(brazilian_text, processed_brazilian_text, "Brazilian text shouldn't be altered.")

    def test_reshaping_arabic_text(self):
        """
        Test reshaping is applied properly on Arabic text.
        """
        text = "بث مباشر"
        processed_text = reshape_text(text)
        expected_shapes = ['ﺮ', 'ﺷ', 'ﺎ', 'ﺒ', 'ﻣ', ' ', 'ﺚ', 'ﺑ']

        for i, expected_shape in enumerate(expected_shapes):
            self.assertEqual(processed_text[i], expected_shape)
