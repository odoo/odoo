from unittest.mock import patch

from odoo.addons.account_edi_ubl_cii.tests.test_ubl_import_bis3_invoice_be import TestUblImportBis3InvoiceBE
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUblImportBis3InvoiceBEAutoGeneratePDF(TestUblImportBis3InvoiceBE):

    def test_import_invoice_auto_generate_pdf(self):
        def _run_wkhtmltopdf(*args, **kwargs):
            _filename, file_content = self._import_file_content('test_import_invoice_auto_generate_pdf', 'pdf')
            return file_content

        def _set_pdf_param(value):
            self.env['ir.config_parameter'].sudo().set_param(
                'account_edi_ubl_cii.disable_pdf_in_xml',
                value
            )
            self.env['ir.config_parameter'].flush_model()

        def _import_and_assert(should_generate_pdf):
            # Import the document that doesn't contain an embedded PDF
            with patch.object(self.env.registry['ir.actions.report'], '_run_wkhtmltopdf', _run_wkhtmltopdf):
                bill = self._import_invoice_as_attachment_on(
                    test_name='test_import_invoice_auto_generate_pdf',
                    journal=self.company_data["default_journal_purchase"].with_context(force_report_rendering=True),
                )

            self.assertTrue(bill.ubl_cii_xml_id)  # Original XML
            self.assertEqual(len(bill.attachment_ids), int(should_generate_pdf))  # Generated PDF
            if should_generate_pdf:
                self.assertTrue(bill.attachment_ids.mimetype, 'pdf')

        # Default behaviour -> Creates PDF
        _import_and_assert(True)

        # Unabled conf -> No PDF
        _set_pdf_param('True')
        _import_and_assert(False)

        # Return default behaviour
        _set_pdf_param('False')
