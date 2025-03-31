# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools.image import base64_to_image
from io import BytesIO
from PIL import Image
import base64


@tagged('post_install', '-at_install')
class TestWebsiteEvent(TransactionCase):

    def test_event_app_name(self):
        website0 = self.env['website'].create({'name': 'Foo'})
        self.assertEqual(website0.events_app_name, 'Foo Events')

        website1 = self.env['website'].create({'name': 'Foo', 'events_app_name': 'Bar Events'})
        self.assertEqual(website1.events_app_name, 'Bar Events')

        website2 = self.env['website'].create({'name': 'Foo'})
        self.assertEqual(website2.events_app_name, 'Foo Events')
        website2.write({'name': 'Bar'})
        self.assertEqual(website2.events_app_name, 'Foo Events')

    def test_compute_app_icon(self):

        # Generate image data for JPEG
        jpeg_image = Image.new('RGB', (60, 30), color=(73, 109, 137))
        jpeg_io = BytesIO()
        jpeg_image.save(jpeg_io, format='JPEG')
        jpeg_image_data = jpeg_io.getvalue()

        # Generate image data for JPG
        jpg_image = Image.new('RGB', (60, 30), color=(73, 109, 137))
        jpg_io = BytesIO()
        jpg_image.save(jpg_io, format='JPEG')
        jpg_image_data = jpg_io.getvalue()

        # Generate image data for PNG
        png_image = Image.new('RGB', (60, 30), color=(73, 109, 137))
        png_io = BytesIO()
        png_image.save(png_io, format='PNG')
        png_image_data = png_io.getvalue()

        # Generate image data for SVG
        svg_image_data = b"""<svg xmlns="http://www.w3.org/2000/svg" width="60" height="30" version="1.1">
                            <rect width="100%" height="100%" fill="rgb(73, 109, 137)"/>
                            </svg>
                        """
        # Image data and their respective expected types
        image_data = {
            'png': png_image_data,
            'jpg': jpg_image_data,
            'jpeg': jpeg_image_data,
            'svg': svg_image_data
        }

        for expected_type, image_data in image_data.items():
            # Create a website record
            website = self.env['website'].create({
                'name': 'Test Website',
                'favicon': base64.b64encode(image_data)
            })

            # Call the method to compute app_icon
            website._compute_app_icon()

            if expected_type in ['jpeg', 'png', 'jpg']:
                # Check if app_icon is set
                self.assertTrue(website.app_icon)

                # Check if app_icon is a valid image
                image = base64_to_image(website.app_icon)
                self.assertEqual(image.format.lower(), 'png')
            else:
                # For SVG images, ensure that the app_icon is not set
                self.assertFalse(website.app_icon)
