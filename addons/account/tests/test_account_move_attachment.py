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
            files={"ufile": b""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(invoice.attachment_ids)
