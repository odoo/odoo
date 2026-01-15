# Part of Odoo. See LICENSE file for full copyright and licensing details.

from PIL import Image

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools.image import base64_to_image, image_to_base64


@tagged('post_install', '-at_install')
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
