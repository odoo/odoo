# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import binascii

from odoo.tools.json import scriptsafe as json_safe
from odoo.addons.http_routing.models.ir_http import slug

import odoo.tests
from odoo.tests.common import HttpCase


@odoo.tests.tagged('-at_install', 'post_install')
class TestController(HttpCase):
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
        # Need to bypass security check to write image with mimetype image/svg+xml
        context = {'binary_field_real_user': self.env['res.users'].sudo().browse([1])}
        attachment = self.env['ir.attachment'].sudo().with_context(context).create({
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
