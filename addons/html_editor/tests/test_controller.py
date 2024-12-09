
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import binascii
import json

import odoo.tests
from odoo.tests.common import HttpCase, new_test_user
from odoo.tools.json import scriptsafe as json_safe


@odoo.tests.tagged('-at_install', 'post_install')
class TestController(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        portal_user = new_test_user(cls.env, login='portal_user', groups='base.group_portal')
        cls.portal_user = portal_user
        cls.portal = portal_user.login
        admin_user = new_test_user(cls.env, login='admin_user', groups='base.group_user,base.group_system')
        cls.admin = admin_user.login
        cls.headers = {"Content-Type": "application/json"}
        cls.pixel = 'R0lGODlhAQABAIAAAP///wAAACwAAAAAAQABAAACAkQBADs='

    def _build_payload(self, params=None):
        """
        Helper to properly build jsonrpc payload
        """
        return {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 0,
            "params": params or {},
        }

    def test_01_upload_document(self):
        self.authenticate('admin', 'admin')
        # Upload document.
        response = self.url_open(
            '/html_editor/attachment/add_data',
            headers={'Content-Type': 'application/json'},
            data=json_safe.dumps({'params': {
                'name': 'test.txt',
                'data': 'SGVsbG8gd29ybGQ=',  # base64 Hello world
                'is_image': False,
            }})
        ).json()
        self.assertFalse('error' in response, 'Upload failed: %s' % response.get('error', {}).get('message'))
        attachment_id = response['result']['id']
        checksum = response['result']['checksum']
        # Download document and check content.
        response = self.url_open(
            '/web/content/%s?unique=%s&download=true' % (attachment_id, checksum)
        )
        self.assertEqual(200, response.status_code, 'Expect response')
        self.assertEqual(b'Hello world', response.content, 'Expect raw content')

        def test_02_illustration_shape(self):
            self.authenticate('admin', 'admin')
            # SVG with all replaceable colors.
            svg = b"""
    <svg viewBox="0 0 400 400">
      <rect width="300" height="300" style="fill:#3AADAA;" />
      <rect x="20" y="20" width="300" height="300" style="fill:#7C6576;" />
      <rect x="40" y="40" width="300" height="300" style="fill:#F6F6F6;" />
      <rect x="60" y="60" width="300" height="300" style="fill:#FFFFFF;" />
      <rect x="80" y="80" width="300" height="300" style="fill:#383E45;" />
    </svg>
            """
            attachment = self.env['ir.attachment'].create({
                'name': 'test.svg',
                'mimetype': 'image/svg+xml',
                'datas': binascii.b2a_base64(svg, newline=False),
                'public': True,
                'res_model': 'ir.ui.view',
                'res_id': 0,
            })
            # Shape illustration with slug.
            slug = self.env['ir.http']._slug
            url = '/html_editor/shape/illustration/%s' % slug(attachment)
            palette = 'c1=%233AADAA&c2=%237C6576&&c3=%23F6F6F6&&c4=%23FFFFFF&&c5=%23383E45'
            attachment['url'] = '%s?%s' % (url, palette)

            response = self.url_open(url)
            self.assertEqual(200, response.status_code, 'Expect response')
            self.assertEqual(svg, response.content, 'Expect unchanged SVG')

            response = self.url_open(url + '?c1=%23ABCDEF')
            self.assertEqual(200, response.status_code, 'Expect response')
            self.assertEqual(len(svg), len(response.content), 'Expect same length as original')
            self.assertTrue('ABCDEF' in str(response.content), 'Expect patched c1')
            self.assertTrue('3AADAA' not in str(response.content), 'Old c1 should not be there anymore')

            # Shape illustration without slug.
            url = '/html_editor/shape/illustration/noslug'
            attachment['url'] = url

            response = self.url_open(url)
            self.assertEqual(200, response.status_code, 'Expect response')
            self.assertEqual(svg, response.content, 'Expect unchanged SVG')

            response = self.url_open(url + '?c1=%23ABCDEF')
            self.assertEqual(200, response.status_code, 'Expect response')
            self.assertEqual(len(svg), len(response.content), 'Expect same length as original')
            self.assertTrue('ABCDEF' in str(response.content), 'Expect patched c1')
            self.assertTrue('3AADAA' not in str(response.content), 'Old c1 should not be there anymore')

    def test_03_get_image_info(self):
        gif_base64 = "R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
        self.authenticate('admin', 'admin')
        # Upload document.
        response = self.url_open(
            '/html_editor/attachment/add_data',
            headers={'Content-Type': 'application/json'},
            data=json_safe.dumps({'params': {
                'name': 'test.gif',
                'data': gif_base64,
                'is_image': True,
            }})
        )
        response = response.json()
        self.assertFalse('error' in response, 'Upload failed: %s' % response.get('error', {}).get('message'))
        attachment_id = response['result']['id']
        image_src = response['result']['image_src']
        mimetype = response['result']['mimetype']
        self.assertEqual('image/gif', mimetype, "Wrong mimetype")
        # Ensure image info can be retrieved.
        response = self.url_open('/html_editor/get_image_info',
                                 headers={'Content-Type': 'application/json'},
                                 data=json_safe.dumps({
                                     "params": {
                                         "src": image_src,
                                     }
                                 }),
                                 )
        response = response.json()
        self.assertEqual(attachment_id, response['result']['original']['id'], "Wrong id")
        self.assertEqual(image_src, response['result']['original']['image_src'], "Wrong image_src")
        self.assertEqual(mimetype, response['result']['original']['mimetype'], "Wrong mimetype")

    def test_04_admin_attachment(self):
        self.authenticate(self.admin, self.admin)
        payload = self._build_payload({"name": "pixel", "data": self.pixel, "is_image": True})
        response = self.url_open('/html_editor/attachment/add_data', data=json.dumps(payload), headers=self.headers)
        self.assertEqual(200, response.status_code)
        attachment = self.env['ir.attachment'].search([('name', '=', 'pixel')])
        self.assertTrue(attachment)

        domain = [('name', '=', 'pixel')]
        result = attachment.search(domain)
        self.assertTrue(len(result), "No attachment fetched")
        self.assertEqual(result, attachment)

    def test_05_internal_link_preview(self):
        self.authenticate(self.admin, self.admin)
        # retrieve metadata of an record without customerized link_preview_name but with display_name
        response_without_preview_name = self.url_open(
            '/html_editor/link_preview_internal',
            data=json_safe.dumps({
                "params": {
                    "preview_url": f"/odoo/users/{self.portal_user.id}",
                }
            }),
            headers=self.headers
        )
        self.assertEqual(200, response_without_preview_name.status_code)
        self.assertTrue('display_name' in response_without_preview_name.text)

        # retrieve metadata of a url with wrong action name
        response_wrong_action = self.url_open(
            '/html_editor/link_preview_internal',
            data=json_safe.dumps({
                "params": {
                    "preview_url": "/odoo/actionInvalid/1",
                }
            }),
            headers=self.headers
        )
        self.assertEqual(200, response_wrong_action.status_code)
        self.assertTrue('error_msg' in response_wrong_action.text)

        # retrieve metadata of a url with wrong record id
        response_wrong_record = self.url_open(
            '/html_editor/link_preview_internal',
            data=json_safe.dumps({
                "params": {
                    "preview_url": "/odoo/users/9999",
                }
            }),
            headers=self.headers
        )
        self.assertEqual(200, response_wrong_record.status_code)
        self.assertTrue('error_msg' in response_wrong_record.text)

        # retrieve metadata of a url not directing to a record
        response_not_record = self.url_open(
            '/html_editor/link_preview_internal',
            data=json_safe.dumps({
                "params": {
                    "preview_url": "/odoo/users",
                }
            }),
            headers=self.headers
        )
        self.assertEqual(200, response_not_record.status_code)
        self.assertTrue('other_error_msg' in response_not_record.text)

        # Attempt to retrieve metadata for path format `odoo/<model>/<record_id>`
        response_model_record = self.url_open(
            '/html_editor/link_preview_internal',
            data=json_safe.dumps({
                "params": {
                    "preview_url": f"/odoo/res.users/{self.portal_user.id}",
                }
            }),
            headers=self.headers
        )
        self.assertEqual(200, response_model_record.status_code)
        self.assertTrue('display_name' in response_model_record.text)
        self.assertIn(self.portal_user.display_name, response_model_record.text)

        # Attempt to retrieve metadata for an abstract model
        response_abstract_model = self.url_open(
            '/html_editor/link_preview_internal',
            data=json_safe.dumps({
                "params": {
                    "preview_url": "/odoo/mail.thread/1",
                }
            }),
            headers=self.headers
        )
        self.assertEqual(200, response_abstract_model.status_code)
        self.assertTrue('error_msg' in response_abstract_model.text)
