# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from odoo.exceptions import AccessError
from odoo.tests.common import tagged, HttpCase, new_test_user
from odoo.tools.misc import mute_logger


class TestAttachmentController(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_user = new_test_user(cls.env, login='portal_user', groups='base.group_portal')
        cls.admin_user = new_test_user(cls.env, login='admin_user', groups='base.group_user,base.group_system')
        cls.headers = {"Content-Type": "application/json"}
        cls.pixel = 'R0lGODlhAQABAIAAAP///wAAACwAAAAAAQABAAACAkQBADs='

    def test_01_portal_attachment(self):
        post = self.env['forum.post'].create({
            "name": "Forum Post Test",
            "forum_id": self.env.ref("website_forum.forum_help").id,
        })
        self.authenticate(self.portal_user.login, self.portal_user.login)
        payload = self.build_rpc_payload({'name': 'pixel', 'data': self.pixel, 'is_image': True, 'res_model': 'forum.post', 'res_id': post.id})
        self.portal_user.karma = 30
        response = self.url_open('/web_editor/attachment/add_data', data=json.dumps(payload), headers=self.headers, timeout=60000)
        self.assertEqual(200, response.status_code)
        attachment = self.env['ir.attachment'].search([('name', '=', 'pixel')])
        self.assertTrue(attachment)

    def test_02_admin_attachment(self):
        self.authenticate(self.admin_user.login, self.admin_user.login)
        payload = self.build_rpc_payload({"name": "pixel", "data": self.pixel, "is_image": True, "res_model": "forum.post"})
        response = self.url_open('/web_editor/attachment/add_data', data=json.dumps(payload), headers=self.headers)
        self.assertEqual(200, response.status_code)
        attachment = self.env['ir.attachment'].search([('name', '=', 'pixel')])
        self.assertTrue(attachment)

        attachment = self.env['ir.attachment'].create([{'name': 'test_pixel', 'public': True, 'res_id': False,
                                                        'mimetype': 'text/plain', 'res_model': 'forum.post',
                                                        'raw': self.pixel, 'website_id': self.env.ref('website.default_website').id}])
        domain = [('name', '=', 'test_pixel')]
        result = attachment.search(domain, limit=1)
        self.assertTrue(result, "No attachment fetched")
        self.assertEqual(result.id, attachment.id)

    @mute_logger('odoo.http')
    def test_03_portal_attachment(self):
        post = self.env['forum.post'].create({
            "name": "Forum Post Test",
            "forum_id": self.env.ref("website_forum.forum_help").id,
        })
        post.forum_id.karma_editor = 0
        self.assertTrue(post.can_use_full_editor)

        with self.assertRaises(AccessError):
            # All the check are done in the controllers,
            # ensure we can not skip them in RPC
            self.env["ir.attachment"].with_user(self.portal_user).create({
                'name': 'test.png',
                'datas': 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
                'res_model': 'forum.post',
                'res_id': post.id,
            })

        self.authenticate('portal_user', 'portal_user')

        # can't upload text file
        response = self.url_open(
            '/html_editor/attachment/add_data',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'params': {
                'name': 'test.txt',
                'data': 'SGVsbG8gd29ybGQ=',  # base64 Hello world
                'is_image': False,
                'res_model': 'forum.post',
                'res_id': post.id,
            }})
        ).json()
        self.assertIn('error', response)
        self.assertIn("Non-internal users can only upload image.", str(response))

        # can upload image file
        response = self.url_open(
            '/html_editor/attachment/add_data',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'params': {
                'name': 'test.png',
                'data': 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',  # base64 image
                'is_image': False,
                'res_model': 'forum.post',
                'res_id': post.id,
            }})
        ).json()
        self.assertNotIn('error', response)

        # try to upload a file larger than the limit
        self.env["ir.config_parameter"].set_int("html_editor.max_portal_file_size", 10)
        response = self.url_open(
            '/html_editor/attachment/add_data',
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'params': {
                'name': 'test.png',
                'data': 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',  # base64 image
                'is_image': False,
                'res_model': 'forum.post',
                'res_id': post.id,
            }})
        ).json()
        self.assertIn('error', response)
        self.assertIn("Non-internal users can't upload large files.", str(response))
