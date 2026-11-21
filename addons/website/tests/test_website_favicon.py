# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import datetime

from PIL import Image

from odoo.tests import tagged
from odoo.tests.common import HttpCase
from odoo.tools.image import base64_to_image, image_to_base64
from unittest.mock import patch


@tagged('post_install', '-at_install')
class TestWebsiteResetPassword(HttpCase):

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

    def test_website_favicon_url(self):
        """
        Test that the favicon url is stable and only changes when
        the favicon itself is changed
        """
        image = Image.new('RGB', (256, 256), color=(135, 90, 123))
        with patch.object(self.env.cr, "now", lambda: datetime.datetime(2026, 10, 20)):
            website = self.env['website'].create({
                'name': 'Test Website',
                'favicon': image_to_base64(image, 'JPEG'),
            })
        favicon_url = website.image_url(website, 'favicon')
        self.assertEqual(
            self.url_open(favicon_url).content,
            base64.b64decode(website.favicon),
        )

        with patch.object(self.env.cr, "now", lambda: datetime.datetime(2026, 10, 21)):
            website.name = 'Test Website, but different'
        self.assertEqual(website.image_url(website, 'favicon'), favicon_url)

        image = Image.new('RGB', (256, 256), color=(144, 2, 7))
        with patch.object(self.env.cr, "now", lambda: datetime.datetime(2026, 10, 22)):
            website.favicon = image_to_base64(image, 'JPEG')
        self.assertNotEqual(website.image_url(website, 'favicon'), favicon_url)
        self.assertEqual(
            self.url_open(website.image_url(website, 'favicon')).content,
            base64.b64decode(website.favicon),
        )
