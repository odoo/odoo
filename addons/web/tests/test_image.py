# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import base64

from PIL import Image
from werkzeug.urls import url_unquote_plus

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
            'mimetype': 'image/gif',
        })

        def remove_prefix(text, prefix):
            if text.startswith(prefix):
                return text[len(prefix):]
            return text

        def assert_filenames(
                url,
                expected_filename,
                expected_filename_star='',
                message=r"File that will be saved on disc should have the original filename without \n and \r",
            ):
            res = self.url_open(url)
            res.raise_for_status()
            if expected_filename_star:
                inline, filename, filename_star = res.headers['Content-Disposition'].split('; ')
            else:
                inline, filename = res.headers['Content-Disposition'].split('; ')
                filename_star = ''

            filename = remove_prefix(filename, "filename=").strip('"')
            filename_star = url_unquote_plus(remove_prefix(filename_star, "filename*=UTF-8''").strip('"'))

            self.assertEqual(inline, 'inline')
            self.assertEqual(filename, expected_filename, message)
            self.assertEqual(filename_star, expected_filename_star, message)

        assert_filenames(f'/web/image/{att.id}',
            r"""foo-l'eb _ a\"!r\".gif""",
            r"""fô☺o-l'éb _ a"!r".gif""",
        )
        assert_filenames(f'/web/image/{att.id}/custom_invalid_name\nis-ok.gif',
            r"""custom_invalid_name_is-ok.gif""",
        )
        assert_filenames(f'/web/image/{att.id}/\r\n',
            r"""__.gif""",
        )
        assert_filenames(f'/web/image/{att.id}/你好',
            r""".gif""",
            r"""你好.gif""",
        )
        assert_filenames(f'/web/image/{att.id}/%E9%9D%A2%E5%9B%BE.gif',
            r""".gif""",
            r"""面图.gif""",
        )
        assert_filenames(f'/web/image/{att.id}/hindi_नमस्ते.gif',
            r"""hindi_.gif""",
            r"""hindi_नमस्ते.gif""",
        )
        assert_filenames(f'/web/image/{att.id}/arabic_مرحبا',
            r"""arabic_.gif""",
            r"""arabic_مرحبا.gif""",
        )
        assert_filenames(f'/web/image/{att.id}/4wzb_!!63148-0-t1.jpg_360x1Q75.jpg_.webp',
            r"""4wzb_!!63148-0-t1.jpg_360x1Q75.jpg_.webp""",
        )
