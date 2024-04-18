# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# TODO in master: rename this file to `test_website` only

from PIL import Image

from odoo.tests import tagged
from odoo.tests.common import HttpCase, TransactionCase
from odoo.tools import base64_to_image, image_to_base64


@tagged('post_install', '-at_install')
# TODO: rename the class name, it's a bad copy paste
class TestWebsiteResetPassword(TransactionCase):

    def test_01_website_favicon(self):
        """The goal of this test is to make sure the favicon is correctly
        handled on the website."""

        # Test setting an Ico file directly, done through create
        Website = self.env['website']

        website = Website.create({
            'name': 'Test Website',
            'favicon': Website._default_favicon(),
        })

        image = base64_to_image(website.favicon)
        self.assertEqual(image.format, 'ICO')

        # Test setting a JPEG file that is too big, done through write
        bg_color = (135, 90, 123)
        image = Image.new('RGB', (1920, 1080), color=bg_color)
        website.favicon = image_to_base64(image, 'JPEG')
        image = base64_to_image(website.favicon)
        self.assertEqual(image.format, 'ICO')
        self.assertEqual(image.size, (256, 256))
        self.assertEqual(image.getpixel((0, 0)), bg_color)


@tagged('-at_install', 'post_install')
class TestWebsiteHttp(HttpCase):
    def test_website_default_social_media(self):
        # Demo data are setting the twitter account of the main company, we need
        # to remove it for demo data to not interfere with the test
        self.env.ref('base.main_company').social_twitter = None
        website = self.env['website'].create({
            'name': 'Test Website',
        })
        self.assertFalse(website.social_twitter)
        r = self.url_open('/website/social/twitter', allow_redirects=False)
        self.assertEqual(r.status_code, 303, "Should redirect to Odoo network")
        self.assertEqual(r.headers.get('Location'), 'https://twitter.com/Odoo', "Should redirect to Odoo network (2)")
