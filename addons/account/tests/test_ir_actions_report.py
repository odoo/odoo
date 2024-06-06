# -*- coding: utf-8 -*-
import base64
import io

from PyPDF2 import PdfFileReader, PdfFileWriter

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tools import pdf
from odoo.tests import tagged
from odoo.tools import file_open


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

        in_invoice_1.message_main_attachment_id = self.env['ir.attachment'].create({
            'datas': base64.b64encode(self.file),
            'name': attach_name,
            'mimetype': 'application/pdf',
            'res_model': 'account.move',
            'res_id': in_invoice_1.id,
        })
        test_record_report = self.env['ir.actions.report'].with_context(force_report_rendering=True)._render_qweb_pdf('account.action_account_original_vendor_bill', res_ids=in_invoice_1.id)
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
        encrypt_version = encrypted_file[encrypt_start: encrypt_end]
        encrypted_file = encrypted_file.replace(encrypt_version, encrypt_version.replace(b'4', b'5'))

        in_invoice_1 = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01'
        })

        in_invoice_1.message_main_attachment_id = self.env['ir.attachment'].create({
            'datas': base64.b64encode(encrypted_file),
            'name': attach_name,
            'mimetype': 'application/pdf',
            'res_model': 'account.move',
            'res_id': in_invoice_1.id,
        })
        test_record_report = self.env['ir.actions.report'].with_context(force_report_rendering=True)._render_qweb_pdf('account.action_account_original_vendor_bill', res_ids=in_invoice_1.id)
        self.assertTrue(test_record_report, "The PDF should have been generated")

        in_invoice_2 = in_invoice_1.copy()

        in_invoice_2.message_main_attachment_id = self.env['ir.attachment'].create({
            'datas': base64.b64encode(self.file),
            'name': attach_name,
            'mimetype': 'application/pdf',
            'res_model': 'account.move',
            'res_id': in_invoice_2.id,
        })
        # trying to merge with a corrupted attachment should not work
        with self.assertRaises(UserError):
            self.env['ir.actions.report'].with_context(force_report_rendering=True)._render_qweb_pdf('account.action_account_original_vendor_bill', res_ids=[in_invoice_1.id, in_invoice_2.id])

    def test_report_with_some_resources_reloaded_from_attachment(self):
        """
        Test for opw-3827700, which caused reports generated for multiple invoices to fail if there was an invoice in
        the middle that had an attachment, and 'Reload from attachment' was enabled for the report. The misbehavior was
        caused by an indexing issue.
        """
        first_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2024-01-01',
            'invoice_date': '2024-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Something',
                'quantity': 1,
                'price_unit': 123,
                'product_id': self.product_a.id
            })]
        })

        second_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2024-01-01',
            'invoice_date': '2024-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Something',
                'quantity': 1,
                'price_unit': 123,
                'product_id': self.product_a.id
            })]
        })

        third_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2024-01-01',
            'invoice_date': '2024-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Something',
                'quantity': 1,
                'price_unit': 123,
                'product_id': self.product_a.id
            })]
        })

        self.assert_invoice_creation([first_invoice, second_invoice, third_invoice], second_invoice)

    def test_report_with_some_resources_reloaded_from_attachment_with_multiple_page_invoice(self):
        """
        Same as @test_report_with_some_resources_reloaded_from_attachment, but tests the behavior for invoices that
        span multiple pages.
        """
        first_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2024-01-01',
            'invoice_date': '2024-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Something',
                'quantity': 1,
                'price_unit': 123,
                'product_id': self.product_a.id
            })]
        })

        second_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2024-01-01',
            'invoice_date': '2024-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'Something ',
                'quantity': 1,
                'price_unit': 123,
                'product_id': self.product_a.id
            })]
        })

        third_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2024-01-01',
            'invoice_date': '2024-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': f'Something #{i}',
                'quantity': 1,
                'price_unit': 123,
                'product_id': self.product_a.id
            }) for i in range(50)]  # Make this a multipage invoice.
        })

        self.assert_invoice_creation([first_invoice, second_invoice, third_invoice], second_invoice)

    def assert_invoice_creation(self, invoices, invoice_to_report):
        self.assertTrue(
            invoice_to_report.id in [invoice.id for invoice in invoices], "Invoice to report must be in invoices list")

        # Post invoices to be able to associate attachments.
        for invoice in invoices:
            invoice.action_post()

        invoices_report_ref = 'account.report_invoice_with_payments'
        reports = self.env['ir.actions.report'].with_context(force_report_rendering=True)

        # Generate report for second invoice to create an attachment.
        second_invoice_report_content, content_type = reports._render_qweb_pdf(invoices_report_ref,
                                                                               res_ids=invoice_to_report.id)
        self.assertEqual(content_type, "pdf", "Report is not a PDF")
        self.assertTrue(second_invoice_report_content, "PDF not generated")

        # Make sure the attachment is created.
        invoices_report = reports._get_report(invoices_report_ref)
        self.assertTrue(invoices_report.attachment, f"Report '{invoices_report_ref}' doesn't save attachments")
        self.assertTrue(invoices_report.retrieve_attachment(invoice_to_report), "Attachment not generated")

        aggregate_report_content, content_type = reports._render_qweb_pdf(invoices_report_ref,
                                                                          res_ids=[invoice.id for invoice in invoices])
        self.assertEqual(content_type, "pdf", "Report is not a PDF")
        self.assertTrue(aggregate_report_content, "PDF not generated")
