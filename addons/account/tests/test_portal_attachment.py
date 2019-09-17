# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import http, tests
from odoo.tools import mute_logger


@tests.tagged('post_install', '-at_install')
class TestUi(tests.HttpCase):

    @mute_logger('odoo.addons.http_routing.models.ir_http', 'odoo.http')
    def test_01_portal_attachment(self):
        """Test the portal chatter attachment route."""

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # For this test we need a parent document with an access_token field
        # (in this case from portal.mixin) and also inheriting mail.thread.
        invoice = self.env['account.move'].with_context(tracking_disable=True).create({
            'name': 'a record with an access_token field',
        })

        # Test public user can't create attachment without token of document
        create_data = {
            'name': "new attachment",
            'res_model': invoice._name,
            'res_id': invoice.id,
            'csrf_token': http.WebRequest.csrf_token(self),
        }
        create_url = base_url + '/portal/attachment/add'
        files = [('file', ('test.txt', b'test', 'plain/text'))]
        res = self.url_open(url=create_url, data=create_data, files=files)
        self.assertEqual(res.status_code, 400)
        self.assertIn("you do not have the rights", res.text)

        # Test public user can create attachment with token
        create_data['access_token'] = invoice._portal_ensure_token()
        res = self.url_open(url=create_url, data=create_data, files=files)
        self.assertEqual(res.status_code, 200)
        create_res = json.loads(res.content.decode('utf-8'))
        self.assertEqual(create_res['name'], "new attachment")

        # Test created attachment is private
        res_binary = self.url_open('/web/content/%d' % create_res['id'])
        self.assertEqual(res_binary.status_code, 404)

        # Test created access_token is working
        res_binary = self.url_open('/web/content/%d?access_token=%s' % (create_res['id'], create_res['access_token']))
        self.assertEqual(res_binary.status_code, 200)

        # Test mimetype is neutered as non-admin
        files = [('file', ('test.svg', b'<svg></svg>', 'image/svg+xml'))]
        res = self.url_open(url=create_url, data=create_data, files=files)
        self.assertEqual(res.status_code, 200)
        create_res = json.loads(res.content.decode('utf-8'))
        self.assertEqual(create_res['mimetype'], 'text/plain')

        res_binary = self.url_open('/web/content/%d?access_token=%s' % (create_res['id'], create_res['access_token']))
        self.assertEqual(res_binary.headers['Content-Type'], 'text/plain')
        self.assertEqual(res_binary.content, b'<svg></svg>')

        res_image = self.url_open('/web/image/%d?access_token=%s' % (create_res['id'], create_res['access_token']))
        self.assertEqual(res_image.headers['Content-Type'], 'text/plain')
        self.assertEqual(res_image.content, b'<svg></svg>')

        # Test attachment can't be removed without valid token
        remove_data = {
            'attachment_id': create_res['id'],
            'access_token': 'wrong',
        }
        remove_url = base_url + '/portal/attachment/remove'
        res = self.opener.post(url=remove_url, json={'params': remove_data})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(self.env['ir.attachment'].search([('id', '=', create_res['id'])]))
        self.assertIn("you do not have the rights", res.text)

        # Test attachment can be removed with token if "pending" state
        remove_data['access_token'] = create_res['access_token']
        res = self.opener.post(url=remove_url, json={'params': remove_data})
        self.assertEqual(res.status_code, 200)
        remove_res = json.loads(res.content.decode('utf-8'))['result']
        self.assertFalse(self.env['ir.attachment'].search([('id', '=', create_res['id'])]))
        self.assertTrue(remove_res is True)

        # Test attachment can't be removed if not "pending" state
        attachment = self.env['ir.attachment'].create({
            'name': "an attachment",
            'access_token': self.env['ir.attachment']._generate_access_token(),
        })
        remove_data = {
            'attachment_id': attachment.id,
            'access_token': attachment.access_token,
        }
        res = self.opener.post(url=remove_url, json={'params': remove_data})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(self.env['ir.attachment'].search([('id', '=', attachment.id)]))
        self.assertIn("not in a pending state", res.text)

        # Test attachment can't be removed if attached to a message
        attachment.write({
            'res_model': 'mail.compose.message',
            'res_id': 0,
        })
        attachment.flush()
        message = self.env['mail.message'].create({
            'attachment_ids': [(6, 0, attachment.ids)],
        })
        remove_data = {
            'attachment_id': attachment.id,
            'access_token': attachment.access_token,
        }
        res = self.opener.post(url=remove_url, json={'params': remove_data})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(attachment.exists())
        self.assertIn("it is linked to a message", res.text)
        message.unlink()

        # Test attachment can't be associated if no attachment token.
        post_url = base_url + '/mail/chatter_post'
        post_data = {
            'res_model': invoice._name,
            'res_id': invoice.id,
            'message': "test message 1",
            'attachment_ids': attachment.id,
            'attachment_tokens': 'false',
            'csrf_token': http.WebRequest.csrf_token(self),
        }
        res = self.url_open(url=post_url, data=post_data)
        self.assertEqual(res.status_code, 400)
        self.assertIn("The attachment %s does not exist or you do not have the rights to access it." % attachment.id, res.text)

        # Test attachment can't be associated if no main document token
        post_data['attachment_tokens'] = attachment.access_token
        res = self.url_open(url=post_url, data=post_data)
        self.assertEqual(res.status_code, 403)
        self.assertIn("Sorry, you are not allowed to access documents of type 'Journal Entries' (account.move).", res.text)

        # Test attachment can't be associated if not "pending" state
        post_data['token'] = invoice._portal_ensure_token()
        self.assertFalse(invoice.message_ids)
        attachment.write({'res_model': 'model'})
        res = self.url_open(url=post_url, data=post_data)
        self.assertEqual(res.status_code, 200)
        invoice.invalidate_cache(fnames=['message_ids'], ids=invoice.ids)
        self.assertEqual(len(invoice.message_ids), 1)
        self.assertEqual(invoice.message_ids.body, "<p>test message 1</p>")
        self.assertFalse(invoice.message_ids.attachment_ids)

        # Test attachment can't be associated if not correct user
        attachment.write({'res_model': 'mail.compose.message'})
        post_data['message'] = "test message 2"
        res = self.url_open(url=post_url, data=post_data)
        self.assertEqual(res.status_code, 200)
        invoice.invalidate_cache(fnames=['message_ids'], ids=invoice.ids)
        self.assertEqual(len(invoice.message_ids), 2)
        self.assertEqual(invoice.message_ids[0].body, "<p>test message 2</p>")
        self.assertFalse(invoice.message_ids.attachment_ids)

        # Test attachment can be associated if all good (complete flow)
        create_data['name'] = "final attachment"
        res = self.url_open(url=create_url, data=create_data, files=files)
        self.assertEqual(res.status_code, 200)
        create_res = json.loads(res.content.decode('utf-8'))
        self.assertEqual(create_res['name'], "final attachment")

        post_data['message'] = "test message 3"
        post_data['attachment_ids'] = create_res['id']
        post_data['attachment_tokens'] = create_res['access_token']
        res = self.url_open(url=post_url, data=post_data)
        self.assertEqual(res.status_code, 200)
        invoice.invalidate_cache(fnames=['message_ids'], ids=invoice.ids)
        self.assertEqual(len(invoice.message_ids), 3)
        self.assertEqual(invoice.message_ids[0].body, "<p>test message 3</p>")
        self.assertEqual(len(invoice.message_ids[0].attachment_ids), 1)
