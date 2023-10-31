# -*- coding: utf-8 -*-
import base64
import io

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tools import pdf
from odoo.tests import tagged
from odoo.tools import file_open

from PyPDF2 import PdfFileReader, PdfFileWriter

@tagged('post_install', '-at_install')
class TestIrActionsReport(AccountTestInvoicingCommon):

    def setUp(self):
        super().setUp()
        self.file = file_open('base/tests/minimal.pdf', 'rb').read()
        self.minimal_reader_buffer = io.BytesIO(self.file)
        self.minimal_pdf_reader = pdf.OdooPdfFileReader(self.minimal_reader_buffer)

    def test_download_one_corrupted_pdf(self):
        """
        PyPDF2 is not flawless. We can upload a PDF that can be previsualised but that cannot be merged by PyPDF2.
        In the case of "Print Original Bills", we want to be able to download the pdf from the list view.
        We test that, when selecting one record, it can be printed (downloaded) without error.
        """
        attach_name = 'original_vendor_bill.pdf'

        in_invoice_1 = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01'
        })

        self.env['ir.attachment'].create({
            'datas': base64.b64encode(self.file),
            'name': attach_name,
            'mimetype': 'application/pdf',
            'res_model': 'account.move',
            'res_id': in_invoice_1.id,
        })
        test_record_report = self.env.ref('account.action_account_original_vendor_bill').with_context(force_report_rendering=True)._render_qweb_pdf(in_invoice_1.id)
        self.assertTrue(test_record_report, "The PDF should have been generated")

    def test_download_one_encrypted_pdf(self):
        """
        Same as test_download_one_corrupted_pdf
        but for encrypted pdf with no password and set encryption type to 5 (not known by PyPDF2)
        """
        attach_name = 'original_vendor_bill.pdf'
        # we need to encrypt the file
        with file_open('base/tests/minimal.pdf', 'rb') as pdf_file:
            pdf_reader = PdfFileReader(pdf_file)
            pdf_writer = PdfFileWriter()
            for page_num in range(pdf_reader.getNumPages()):
                pdf_writer.addPage(pdf_reader.getPage(page_num))
            # Encrypt the PDF
            pdf_writer.encrypt('', use_128bit=True)
            # Get the binary
            output_buffer = io.BytesIO()
            pdf_writer.write(output_buffer)
            encrypted_file = output_buffer.getvalue()

        # we need to change the encryption value from 4 to 5 to simulate an encryption not used by PyPDF2
        encrypt_start = encrypted_file.find(b'/Encrypt')
        encrypt_end = encrypted_file.find(b'>>', encrypt_start)
        encrypt_version = encrypted_file[encrypt_start : encrypt_end]
        encrypted_file = encrypted_file.replace(encrypt_version, encrypt_version.replace(b'4', b'5'))

        in_invoice_1 = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01'
        })

        self.env['ir.attachment'].create({
            'datas': base64.b64encode(encrypted_file),
            'name': attach_name,
            'mimetype': 'application/pdf',
            'res_model': 'account.move',
            'res_id': in_invoice_1.id,
        })
        test_record_report = self.env.ref('account.action_account_original_vendor_bill').with_context(force_report_rendering=True)._render_qweb_pdf(in_invoice_1.id)
        self.assertTrue(test_record_report, "The PDF should have been generated")

        in_invoice_2 = in_invoice_1.copy()

        self.env['ir.attachment'].create({
            'datas': base64.b64encode(self.file),
            'name': attach_name,
            'mimetype': 'application/pdf',
            'res_model': 'account.move',
            'res_id': in_invoice_2.id,
        })
        # trying to merge with a corrupted attachment should not work
        with self.assertRaises(UserError):
            self.env.ref('account.action_account_original_vendor_bill').with_context(force_report_rendering=True)._render_qweb_pdf(res_ids=[in_invoice_1.id, in_invoice_2.id])
