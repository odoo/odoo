# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.json import scriptsafe as json_safe

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
