# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import http, tests
from odoo.tools import mute_logger


@tests.tagged('post_install', '-at_install')
class TestUi(tests.HttpCase):

    @mute_logger('odoo.addons.website.models.ir_http', 'odoo.http')
    def test_01_portal_attachment(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # For this test we need a parent document with an access_token field:
        # attachment itself has an access_token so we can use it as parent too.
        record = self.env['ir.attachment'].create({
            'name': 'a record with an access_token field',
        })

        # Test public user can't create attachment without token of document
        create_data = {
            'name': "new attachment",
            'res_model': record._name,
            'res_id': record.id,
            'csrf_token': http.WebRequest.csrf_token(self),
        }
        create_url = base_url + '/portal/attachment/add'
        files = [('file', ('test.txt', b'test', 'plain/text'))]
        res = self.url_open(url=create_url, data=create_data, files=files)
        self.assertEqual(res.status_code, 400)
        self.assertTrue("you do not have the rights" in res.text)

        # Test public user can create attachment with token
        create_data['access_token'] = record.generate_access_token()[0]
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
        self.assertTrue("you do not have the rights" in res.text)

        # Test attachment can be removed with token if "pending" state
        remove_data['access_token'] = create_res['access_token']
        res = self.opener.post(url=remove_url, json={'params': remove_data})
        self.assertEqual(res.status_code, 200)
        remove_res = json.loads(res.content.decode('utf-8'))['result']
        self.assertFalse(self.env['ir.attachment'].search([('id', '=', create_res['id'])]))
        self.assertTrue(remove_res is True)

        # Test attachment can't be removed if not "pending" state
        remove_data = {
            'attachment_id': record.id,
            'access_token': record.access_token,
        }
        res = self.opener.post(url=remove_url, json={'params': remove_data})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(self.env['ir.attachment'].search([('id', '=', record.id)]))
        self.assertTrue("not in a pending state" in res.text)

        # Test attachment can't be removed if attached to a message
        attachment = self.env['ir.attachment'].create({
            'name': 'a record with an access_token field',
            'res_model': 'mail.compose.message',
            'res_id': 0,
            'access_token': self.env['ir.attachment']._generate_access_token(),
        })
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
        self.assertTrue("it is linked to a message" in res.text)
        message.unlink()

        # Need a `mail.thread` record for the following test
        thread_record = self.env['mail.channel'].create({
            'name': 'channel',
            'public': 'public',
        })
        # Authenticate because public user can't create `mail.message` without
        # token, and `mail.channel` does not have an access_token.
        self.authenticate('portal', 'portal')

        # Test attachment can't be associated if no token.
        post_url = base_url + '/mail/chatter_post'
        post_data = {
            'res_model': thread_record._name,
            'res_id': thread_record.id,
            'message': "test message",
            'attachment_ids': attachment.id,
            'attachment_tokens': 'false',
            'csrf_token': http.WebRequest.csrf_token(self),
        }
        self.assertFalse(thread_record.message_ids)
        res = self.url_open(url=post_url, data=post_data)
        thread_record.invalidate_cache(fnames=['message_ids'], ids=thread_record.ids)
        message = thread_record.message_ids[0]
        self.assertFalse(message.attachment_ids)

        # Test attachment can't be associated if not "pending" state
        post_data['attachment_tokens'] = attachment.access_token
        attachment.write({'res_model': 'model'})
        res = self.url_open(url=post_url, data=post_data)
        thread_record.invalidate_cache(fnames=['message_ids'], ids=thread_record.ids)
        message = thread_record.message_ids[0]
        self.assertFalse(message.attachment_ids)

        # Test attachment can be associated if all good
        attachment.write({'res_model': 'mail.compose.message'})
        res = self.url_open(url=post_url, data=post_data)
        thread_record.invalidate_cache(fnames=['message_ids'], ids=thread_record.ids)
        message = thread_record.message_ids[0]
        self.assertEqual(len(message.attachment_ids), 1)
