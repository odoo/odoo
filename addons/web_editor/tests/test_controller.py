# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import binascii
import json

from io import BytesIO
from PIL import Image

from odoo.tests.common import HttpCase, new_test_user, tagged
from odoo.tools.json import scriptsafe as json_safe
from odoo.tools.misc import file_open

from odoo.addons.http_routing.models.ir_http import slug


@tagged('-at_install', 'post_install')
class TestController(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        portal_user = new_test_user(cls.env, login='portal_user', groups='base.group_portal')
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
            '/web_editor/attachment/add_data',
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
        url = '/web_editor/shape/illustration/%s' % slug(attachment)
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
        url = '/web_editor/shape/illustration/noslug'
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
            '/web_editor/attachment/add_data',
            headers={'Content-Type': 'application/json'},
            data=json_safe.dumps({'params': {
                'name': 'test.gif',
                'data': gif_base64,
                'is_image': True,
            }})
        ).json()
        self.assertFalse('error' in response, 'Upload failed: %s' % response.get('error', {}).get('message'))
        attachment_id = response['result']['id']
        image_src = response['result']['image_src']
        mimetype = response['result']['mimetype']
        self.assertEqual('image/gif', mimetype, "Wrong mimetype")
        # Ensure image info can be retrieved.
        response = self.url_open('/web_editor/get_image_info',
            headers={'Content-Type': 'application/json'},
            data=json_safe.dumps({
                "params": {
                    "src": image_src,
                }
            }),
        ).json()
        self.assertEqual(attachment_id, response['result']['original']['id'], "Wrong id")
        self.assertEqual(image_src, response['result']['original']['image_src'], "Wrong image_src")
        self.assertEqual(mimetype, response['result']['original']['mimetype'], "Wrong mimetype")

    def test_04_admin_attachment(self):
        self.authenticate(self.admin, self.admin)
        payload = self._build_payload({"name": "pixel", "data": self.pixel, "is_image": True})
        response = self.url_open('/web_editor/attachment/add_data', data=json.dumps(payload), headers=self.headers)
        self.assertEqual(200, response.status_code)
        attachment = self.env['ir.attachment'].search([('name', '=', 'pixel')])
        self.assertTrue(attachment)

        domain = [('name', '=', 'pixel')]
        result = attachment.search(domain)
        self.assertTrue(len(result), "No attachment fetched")
        self.assertEqual(result, attachment)

    def test_font_to_img(self):
        # This test was introduced because the play button was cropped in noble following some adaptation.
        # This test is able to reproduce the issue and ensure that the expected result is the right one
        # comparing image is not ideal, but this should work in most case, maybe adapted if the font is changed.

        response = self.url_open(
            "/web_editor/font_to_img/61802/rgb(0,143,140)/rgb(255,255,255)/190x200"
        )

        img = Image.open(BytesIO(response.content))
        self.assertEqual(
            img.size,
            (201, 200),
            "Looks strange regarding request but this is the current result",
        )
        # Image is a play button
        img_reference = Image.open(file_open("web_editor/tests/play.png", "rb"))
        self.assertEqual(img, img_reference, "Result image should be the play button")
