from odoo import http
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, HttpCase


@tagged("-at_install", "post_install")
class TestAccountMoveAttachmentHttp(HttpCase):

    def test_preserving_manually_added_attachments(self):
        """ Preserve attachments manually added (not coming from emails) to an invoice """
        self.authenticate("admin", "admin")

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
        })
        self.assertFalse(invoice.attachment_ids)
        response = self.url_open("/mail/attachment/upload",
            {
                "csrf_token": http.Request.csrf_token(self),
                "thread_id": invoice.id,
                "thread_model": "account.move",
            },
            files={'ufile': ('salut.txt', b"Salut !\n", 'text/plain')},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(invoice.attachment_ids)


@tagged("-at_install", "post_install")
class TestAccountMoveAttachmentInvoicing(AccountTestInvoicingCommon):

    def test_save_manually_printed_attachments(self):
        """
        When manually printing invoice's attachment (via the cog button),
        and when the "Save as Attachment Prefix" setting is saved for that action,
        the new attachment should also be saved in the invoice field that refers this attachment: 'invoice_pdf_report_file'
        """
        invoice_report = self.env['ir.actions.report'].search([('report_name', '=', 'account.report_invoice_with_payments')])
        invoice_report.attachment = "object.name"  # activate setting to save as attachment when printing

        # Create invoice and print the PDF manually
        invoice = self.init_invoice('out_invoice', amounts=[1000], post=True)
        self.env['ir.actions.report'] \
            .with_context(force_report_rendering=True) \
            ._render_qweb_pdf(invoice_report, invoice.ids)

        self.assertTrue(invoice.invoice_pdf_report_file)
        self.assertTrue(invoice.invoice_pdf_report_id)
