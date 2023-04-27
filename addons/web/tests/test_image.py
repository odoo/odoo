# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import base64

from PIL import Image

from odoo.http import content_disposition
from odoo.tests.common import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestImage(HttpCase):
    def test_01_content_image_resize_placeholder(self):
        """The goal of this test is to make sure the placeholder image is
        resized appropriately depending on the given URL parameters."""

        # CASE: resize placeholder, given size but original ratio is always kept
        response = self.url_open('/web/image/0/200x150')
        image = Image.open(io.BytesIO(response.content))
        self.assertEqual(image.size, (150, 150))

        # CASE: resize placeholder to 128
        response = self.url_open('/web/image/fake/0/image_128')
        image = Image.open(io.BytesIO(response.content))
        self.assertEqual(image.size, (128, 128))

        # CASE: resize placeholder to 256
        response = self.url_open('/web/image/fake/0/image_256')
        image = Image.open(io.BytesIO(response.content))
        self.assertEqual(image.size, (256, 256))

        # CASE: resize placeholder to 1024 (but placeholder image is too small)
        response = self.url_open('/web/image/fake/0/image_1024')
        image = Image.open(io.BytesIO(response.content))
        self.assertEqual(image.size, (256, 256))

        # CASE: no size found, use placeholder original size
        response = self.url_open('/web/image/fake/0/image_no_size')
        image = Image.open(io.BytesIO(response.content))
        self.assertEqual(image.size, (256, 256))

    def test_02_content_image_Etag_304(self):
        """This test makes sure that the 304 response is properly returned if the ETag is properly set"""

        attachment = self.env['ir.attachment'].create({
            'datas': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
            'name': 'testEtag.gif',
            'public': True,
            'mimetype': 'image/gif',
        })
        response = self.url_open('/web/image/%s' % attachment.id, timeout=None)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(base64.b64encode(response.content), attachment.datas)

        etag = response.headers.get('ETag')

        response2 = self.url_open('/web/image/%s' % attachment.id, headers={"If-None-Match": etag})
        self.assertEqual(response2.status_code, 304)
        self.assertEqual(len(response2.content), 0)

    def test_03_web_content_filename(self):
        """This test makes sure the Content-Disposition header matches the given filename"""

        att = self.env['ir.attachment'].create({
            'datas': b'R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=',
            'name': 'testFilename.gif',
            'public': True,
            'mimetype': 'image/gif'
        })

        # CASE: no filename given
        res = self.url_open('/web/image/%s/0x0/?download=true' % att.id)
        self.assertEqual(res.headers['Content-Disposition'], content_disposition('testFilename.gif'))

        # CASE: given filename without extension
        res = self.url_open('/web/image/%s/0x0/custom?download=true' % att.id)
        self.assertEqual(res.headers['Content-Disposition'], content_disposition('custom.gif'))

        # CASE: given filename and extention
        res = self.url_open('/web/image/%s/0x0/custom.png?download=true' % att.id)
        self.assertEqual(res.headers['Content-Disposition'], content_disposition('custom.png'))
