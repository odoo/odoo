# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon
from odoo.tests.common import tagged

import json

from odoo import http
from odoo.tools import file_open, mute_logger


@tagged('post_install', '-at_install')
class TestPortalAttachment(AccountTestInvoicingHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.out_invoice = cls.env['account.move'].with_context(tracking_disable=True).create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 100.0}),
            ],
        })

        cls.invoice_base_url = cls.out_invoice.get_base_url()

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_01_portal_attachment(self):
        """Test the portal chatter attachment route."""
        self.partner_a.write({  # ensure an email for message_post
            'email': 'partner.a@test.example.com',
        })

        self.authenticate(None, None)

        # Test public user can't create attachment without token of document
        with file_open("addons/web/__init__.py") as file:
            res = self.url_open(
                url=f"{self.invoice_base_url}/mail/attachment/upload",
                data={
                    "csrf_token": http.Request.csrf_token(self),
                    "thread_id": self.out_invoice.id,
                    "thread_model": self.out_invoice._name,
                },
                files={"ufile": file},
            )
        self.assertEqual(res.status_code, 404)
        self.assertIn("The requested URL was not found on the server.", res.text)

        # Test public user can create attachment with token
        with file_open("addons/web/__init__.py") as file:
            res = self.url_open(
                url=f"{self.invoice_base_url}/mail/attachment/upload",
                data={
                    "csrf_token": http.Request.csrf_token(self),
                    "thread_id": self.out_invoice.id,
                    "thread_model": self.out_invoice._name,
                    "token": self.out_invoice._portal_ensure_token(),
                },
                files={"ufile": file},
            )
        self.assertEqual(res.status_code, 200)
        create_res = json.loads(res.content.decode('utf-8'))['data']['ir.attachment'][0]
        self.assertTrue(self.env['ir.attachment'].sudo().search([('id', '=', create_res['id'])]))

        # Test created attachment is private
        res_binary = self.url_open('/web/content/%d' % create_res['id'])
        self.assertEqual(res_binary.status_code, 404)

        # Test created access_token is working
        res_binary = self.url_open(
            "/web/content/%d?access_token=%s"
            % (create_res["id"], create_res["raw_access_token"])
        )
        self.assertEqual(res_binary.status_code, 200)

        # Test mimetype is neutered as non-admin
        res = self.url_open(
            url=f"{self.invoice_base_url}/mail/attachment/upload",
            data={
                "csrf_token": http.Request.csrf_token(self),
                "is_pending": True,
                "thread_id": self.out_invoice.id,
                "thread_model": self.out_invoice._name,
                "token": self.out_invoice._portal_ensure_token(),
            },
            files={"ufile": ("test.svg", b'<svg></svg>', "image/svg+xml")},
        )
        self.assertEqual(res.status_code, 200)
        create_res = json.loads(res.content.decode('utf-8'))['data']['ir.attachment'][0]
        self.assertEqual(create_res['mimetype'], 'text/plain')

        res_binary = self.url_open(
            "/web/content/%d?access_token=%s"
            % (create_res["id"], create_res["raw_access_token"])
        )
        self.assertEqual(res_binary.headers['Content-Type'], 'text/plain; charset=utf-8')
        self.assertEqual(res_binary.content, b'<svg></svg>')

        res_image = self.url_open(
            "/web/image/%d?access_token=%s"
            % (create_res["id"], create_res["raw_access_token"])
        )
        self.assertEqual(res_image.headers['Content-Type'], 'application/octet-stream')
        self.assertEqual(res_image.content, b'<svg></svg>')

        # Test attachment can't be removed without valid token
        res = self.url_open(
            url=f'{self.invoice_base_url}/mail/attachment/delete',
            json={
                'params': {
                    'attachment_id': create_res['id'],
                    'access_token': "wrong",
                },
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(self.env['ir.attachment'].sudo().search([('id', '=', create_res['id'])]))
        self.assertIn("The requested URL was not found on the server.", res.text)

        # Test attachment can be removed with token if "pending" state
        res = self.url_open(
            url=f'{self.invoice_base_url}/mail/attachment/delete',
            json={
                'params': {
                    'attachment_id': create_res['id'],
                    "access_token": create_res["ownership_token"],
                },
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(self.env['ir.attachment'].sudo().search([('id', '=', create_res['id'])]))

        # Test attachment can be removed with token if not "pending" state
        attachment = self.env['ir.attachment'].create({
            'name': 'an attachment',
        })
        res = self.url_open(
            url=f'{self.invoice_base_url}/mail/attachment/delete',
            json={
                'params': {
                    'attachment_id': attachment.id,
                    "access_token": attachment._get_ownership_token(),
                },
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(self.env['ir.attachment'].sudo().search([('id', '=', attachment.id)]))

        # Test attachment can be removed if attached to a message
        attachment = self.env["ir.attachment"].create({
            "name": "an attachment",
            "res_model": "mail.compose.message",
            "res_id": 0,
        })
        attachment.flush_recordset()
        message = self.env['mail.message'].create({
            'attachment_ids': [(6, 0, attachment.ids)],
        })
        res = self.url_open(
            url=f'{self.invoice_base_url}/mail/attachment/delete',
            json={
                'params': {
                    'attachment_id': attachment.id,
                    "access_token": attachment._get_ownership_token(),
                },
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(attachment.exists())
        message.sudo().unlink()

        # Test attachment can't be associated if no attachment token.
        attachment = self.env['ir.attachment'].create({
            'name': 'an attachment',
            'res_model': 'mail.compose.message',
            'res_id': 0,
        })
        res = self.url_open(
            url=f'{self.invoice_base_url}/mail/message/post',
            json={
                'params': {
                    'thread_model': self.out_invoice._name,
                    'thread_id': self.out_invoice.id,
                    'post_data': {
                        'body': "test message 1",
                        'attachment_ids': [attachment.id],
                        "attachment_tokens": ["false"],
                    },
                    "token": self.out_invoice._portal_ensure_token(),
                },
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn(
            "One or more attachments do not exist, or you do not have the rights to access them.",
            res.text,
        )

        # Test attachment can't be associated if no main document token
        res = self.url_open(
            url=f'{self.invoice_base_url}/mail/message/post',
            json={
                'params': {
                    'thread_model': self.out_invoice._name,
                    'thread_id': self.out_invoice.id,
                    "post_data": {
                        "body": "test message 1",
                        'attachment_ids': [attachment.id],
                        "attachment_tokens": [attachment._get_ownership_token()],
                    },
                },
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("The requested URL was not found on the server.", res.text)

        # Test attachment can't be associated if not "pending" state
        # not messages which are sent by `_post_add_create` in the previous steps
        self.assertFalse(
            self.out_invoice.message_ids.filtered(lambda m: m.author_id == self.partner_a))
        attachment.write({'res_model': 'model'})
        res = self.url_open(
            url=f'{self.invoice_base_url}/mail/message/post',
            json={
                'params': {
                    'thread_model': self.out_invoice._name,
                    'thread_id': self.out_invoice.id,
                    "post_data": {
                        "body": "test message 1",
                        "attachment_ids": [attachment.id],
                        "attachment_tokens": [attachment._get_ownership_token()],
                    },
                    'token': self.out_invoice._portal_ensure_token(),
                },
            },
        )
        self.assertEqual(res.status_code, 200)
        self.out_invoice.invalidate_recordset(['message_ids'])
        # not messages which are sent by `_post_add_create` in the previous steps
        message = self.out_invoice.message_ids.filtered(lambda m: m.author_id == self.partner_a)
        self.assertEqual(len(message), 1)
        self.assertEqual(message.body, "<p>test message 1</p>")
        self.assertFalse(message.attachment_ids)

        # Test attachment can't be associated if not correct user
        attachment.write({'res_model': 'mail.compose.message'})
        res = self.url_open(
            url=f'{self.invoice_base_url}/mail/message/post',
            json={
                'params': {
                    'thread_model': self.out_invoice._name,
                    'thread_id': self.out_invoice.id,
                    "post_data": {
                        "body": "test message 2",
                        "attachment_ids": [attachment.id],
                        "attachment_tokens": [attachment._get_ownership_token()],
                    },
                    'token': self.out_invoice._portal_ensure_token(),
                },
            },
        )
        self.assertEqual(res.status_code, 200)
        self.out_invoice.invalidate_recordset(['message_ids'])
        # not messages which are sent by `_post_add_create` in the previous steps
        messages = self.out_invoice.message_ids.filtered(lambda m: m.author_id == self.partner_a)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].author_id, self.partner_a)
        self.assertEqual(messages[0].body, "<p>test message 2</p>")
        self.assertEqual(messages[0].email_from, self.partner_a.email_formatted)
        self.assertFalse(messages.attachment_ids)

        # Test attachment can be associated if all good (complete flow)
        res = self.url_open(
            url=f"{self.invoice_base_url}/mail/attachment/upload",
            data={
                "csrf_token": http.Request.csrf_token(self),
                "is_pending": True,
                "thread_id": self.out_invoice.id,
                "thread_model": self.out_invoice._name,
                "token": self.out_invoice._portal_ensure_token(),
            },
            files={"ufile": ("final attachment", b'test', "plain/text")},
        )
        self.assertEqual(res.status_code, 200)
        create_res = json.loads(res.content.decode('utf-8'))['data']['ir.attachment'][0]
        self.assertEqual(create_res['name'], "final attachment")

        res = self.url_open(
            url=f'{self.invoice_base_url}/mail/message/post',
            json={
                'params': {
                    'thread_model': self.out_invoice._name,
                    'thread_id': self.out_invoice.id,
                    "post_data": {
                        "body": "test message 3",
                        "attachment_ids": [create_res['id']],
                        "attachment_tokens": [create_res["ownership_token"]],
                    },
                    'token': self.out_invoice._portal_ensure_token(),
                },
            },
        )
        self.assertEqual(res.status_code, 200)
        self.out_invoice.invalidate_recordset(['message_ids'])
        # not messages which are sent by `_post_add_create` in previous steps
        messages = self.out_invoice.message_ids.filtered(lambda m: m.author_id == self.partner_a)
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0].body, "<p>test message 3</p>")
        self.assertEqual(len(messages[0].attachment_ids), 1)
