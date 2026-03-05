from odoo import http
from odoo.tests import tagged, HttpCase


@tagged("-at_install", "post_install")
class TestAccountMoveAttachment(HttpCase):

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

    def test_create_records_from_empty_pdf_attachment(self):
        """Ensure importing an empty PDF attachment does not crash and still returns created records."""
        attachment = self.env['ir.attachment'].create({
            'name': 'invoice.pdf',
            'mimetype': 'application/pdf',
        })
        records = self.env['account.move']._create_records_from_attachments(attachment)
        self.assertTrue(records)
