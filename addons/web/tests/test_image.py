# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import base64

from PIL import Image
from werkzeug.urls import url_quote

from odoo.tests.common import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestImage(HttpCase):
    def test_01_content_image_resize_placeholder(self):
        """The goal of this test is to make sure the placeholder image is
        resized appropriately depending on the given URL parameters."""

        # CASE: resize placeholder, given size but original ratio is always kept
        response = self.url_open('/web/image/0/200x150')
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content))
        self.assertEqual(image.size, (150, 150))

        # CASE: resize placeholder to 128
        response = self.url_open('/web/image/fake/0/image_128')
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content))
        self.assertEqual(image.size, (128, 128))

        # CASE: resize placeholder to 256
        response = self.url_open('/web/image/fake/0/image_256')
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content))
        self.assertEqual(image.size, (256, 256))

        # CASE: resize placeholder to 1024 (but placeholder image is too small)
        response = self.url_open('/web/image/fake/0/image_1024')
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content))
        self.assertEqual(image.size, (256, 256))

        # CASE: no size found, use placeholder original size
        response = self.url_open('/web/image/fake/0/image_no_size')
        response.raise_for_status()
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
        response.raise_for_status()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(base64.b64encode(response.content), attachment.datas)

        etag = response.headers.get('ETag')

        response2 = self.url_open('/web/image/%s' % attachment.id, headers={"If-None-Match": etag})
        response2.raise_for_status()
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
        res.raise_for_status()
        self.assertEqual(res.headers['Content-Disposition'], 'attachment; filename=testFilename.gif')

        # CASE: given filename without extension
        res = self.url_open('/web/image/%s/0x0/custom?download=true' % att.id)
        res.raise_for_status()
        self.assertEqual(res.headers['Content-Disposition'], 'attachment; filename=custom.gif')

        # CASE: given filename and extention
        res = self.url_open('/web/image/%s/0x0/custom.png?download=true' % att.id)
        res.raise_for_status()
        self.assertEqual(res.headers['Content-Disposition'], 'attachment; filename=custom.png')

    def test_04_web_content_filename_secure(self):
        """This test makes sure the Content-Disposition header matches the given filename"""

        att = self.env['ir.attachment'].create({
            'datas': b'R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=',
            'name': """fô☺o-l'éb \n a"!r".gif""",
            'public': True,
            'mimetype': 'image/gif'
        })

        res = self.url_open(f'/web/image/{att.id}')
        expected_ufilename = url_quote(att.name.replace('\n', '_').replace('\r', '_'))
        self.assertEqual(res.headers['Content-Disposition'], r"""inline; filename="foo-l'eb _ a\"!r\".gif"; filename*=UTF-8''""" + expected_ufilename)
        res.raise_for_status()

        res = self.url_open(f'/web/image/{att.id}/custom_invalid_name\nis-ok.gif')
        self.assertEqual(res.headers['Content-Disposition'], 'inline; filename=custom_invalid_name_is-ok.gif')
        res.raise_for_status()

        res = self.url_open(f'/web/image/{att.id}/\r\n')
        self.assertEqual(res.headers['Content-Disposition'], 'inline; filename=__.gif')
        res.raise_for_status()

        res = self.url_open(f'/web/image/{att.id}/你好')
        self.assertEqual(res.headers['Content-Disposition'], 'inline; filename=.gif; filename*=UTF-8\'\'%E4%BD%A0%E5%A5%BD.gif')
        res.raise_for_status()

        res = self.url_open(f'/web/image/{att.id}/%E9%9D%A2%E5%9B%BE.gif')
        self.assertEqual(res.headers['Content-Disposition'], 'inline; filename=.gif; filename*=UTF-8\'\'%E9%9D%A2%E5%9B%BE.gif')
        res.raise_for_status()

        res = self.url_open(f'/web/image/{att.id}/hindi_नमस्ते.gif')
        self.assertEqual(res.headers['Content-Disposition'], 'inline; filename=hindi_.gif; filename*=UTF-8\'\'hindi_%E0%A4%A8%E0%A4%AE%E0%A4%B8%E0%A5%8D%E0%A4%A4%E0%A5%87.gif')
        res.raise_for_status()
        res = self.url_open(f'/web/image/{att.id}/arabic_مرحبا.gif')
        self.assertEqual(res.headers['Content-Disposition'], 'inline; filename=arabic_.gif; filename*=UTF-8\'\'arabic_%D9%85%D8%B1%D8%AD%D8%A8%D8%A7.gif')
        res.raise_for_status()

        res = self.url_open(f'/web/image/{att.id}/4wzb_!!63148-0-t1.jpg_360x1Q75.jpg_.webp')
        self.assertEqual(res.headers['Content-Disposition'], 'inline; filename=4wzb_!!63148-0-t1.jpg_360x1Q75.jpg_.webp')
        res.raise_for_status()
