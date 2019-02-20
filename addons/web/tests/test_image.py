# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io

from PIL import Image

from odoo.tests.common import HttpCase


class TestImage(HttpCase):
    def test_01_content_image_resize_placeholder(self):
        """The goal of this test is to make sure the placeholder image is
        resized appropriately depending on the given URL parameters."""

        # CASE: resize placeholder to given size
        response = self.url_open('/web/image/0/200x150')
        image = Image.open(io.BytesIO(response.content))
        self.assertEqual(image.size, (200, 150))

        # CASE: resize placeholder to small
        response = self.url_open('/web/image/fake/0/image_small')
        image = Image.open(io.BytesIO(response.content))
        self.assertEqual(image.size, (64, 64))

        # CASE: resize placeholder to medium
        response = self.url_open('/web/image/fake/0/image_medium')
        image = Image.open(io.BytesIO(response.content))
        self.assertEqual(image.size, (128, 128))

        # CASE: resize placeholder to large
        response = self.url_open('/web/image/fake/0/image_large')
        image = Image.open(io.BytesIO(response.content))
        self.assertEqual(image.size, (256, 256))

        # CASE: resize placeholder to big (but placeholder image is too small)
        response = self.url_open('/web/image/fake/0/image')
        image = Image.open(io.BytesIO(response.content))
        self.assertEqual(image.size, (256, 256))

        # CASE: no size found, use placeholder original size
        response = self.url_open('/web/image/fake/0/image_no_size')
        image = Image.open(io.BytesIO(response.content))
        self.assertEqual(image.size, (256, 256))
