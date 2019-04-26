# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import binascii
import PIL

from odoo import tools
from odoo.tests.common import TransactionCase


class TestImage(TransactionCase):
    """Tests for the different image tools helpers.

    The following helpers are not tested here because they are wrappers for the
    other methods or they are tested elsewhere (eg. on TestWebsiteSaleImage):
    - image_get_resized_images
    - image_resize_images
    - is_image_size_above
    """
    def setUp(self):
        super(TestImage, self).setUp()
        # This is the base64 of a 1px * 1px image saved as PNG.
        self.base64_image_1x1 = b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC'
        self.base64_svg = base64.b64encode(b'<svg></svg>')
        self.base64_image_1920_1080 = tools.image_to_base64(PIL.Image.new('RGB', (1920, 1080)), 'JPEG')

    def test_00_base64_to_image(self):
        """Test that base64 is correctly opened as a PIL image."""

        # CASE: base64 as bytes
        image = tools.base64_to_image(self.base64_image_1x1)
        self.assertEqual(type(image), PIL.PngImagePlugin.PngImageFile)
        self.assertEqual(image.size, (1, 1))

        # CASE: base64 as string
        image = tools.base64_to_image(self.base64_image_1x1.decode('ASCII'))
        self.assertEqual(type(image), PIL.PngImagePlugin.PngImageFile)
        self.assertEqual(image.size, (1, 1))

        # CASE: wrong base64: binascii.Error: Incorrect padding
        with self.assertRaises(binascii.Error):
            image = tools.base64_to_image(b'oazdazpodazdpok')

        # CASE: wrong base64: OSError: cannot identify image file
        with self.assertRaises(OSError):
            image = tools.base64_to_image(b'oazdazpodazdpokd')

    def test_01_image_to_base64(self):
        """Test that a PIL image is correctly saved as base64."""
        image = PIL.Image.new('RGB', (1, 1))
        image_base64 = tools.image_to_base64(image, 'PNG')
        self.assertEqual(image_base64, self.base64_image_1x1)

    def test_10_image_process_resize(self):
        """Test that image_process is working as expected for resizeing."""

        # CASE: return False if base64_source is falsy
        res = tools.image_process(False)
        self.assertFalse(res)

        # CASE: return base64_source if format is SVG
        res = tools.image_process(self.base64_svg)
        self.assertEqual(res, self.base64_svg)

        # CASE: correct resize (keep ratio)
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, size=(800, 600)))
        self.assertEqual(image.size, (800, 450))

        # CASE: change format to PNG
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, output_format='PNG'))
        self.assertEqual(image.format, 'PNG')

        # CASE: change format to JPEG (case insensitive)
        image = tools.base64_to_image(tools.image_process(self.base64_image_1x1, output_format='jpeg'))
        self.assertEqual(image.format, 'JPEG')

        # CASE: change format to BMP converted to PNG
        image = tools.base64_to_image(tools.image_process(self.base64_image_1x1, output_format='BMP'))
        self.assertEqual(image.format, 'PNG')

        # CASE: change format PNG with RGBA to JPEG
        base64_image_1080_1920_rgba = tools.image_to_base64(PIL.Image.new('RGBA', (1080, 1920)), 'PNG')
        image = tools.base64_to_image(tools.image_process(base64_image_1080_1920_rgba, output_format='jpeg'))
        self.assertEqual(image.format, 'JPEG')

        # CASE: keep ratio if no height given
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, size=(192, None)))
        self.assertEqual(image.size, (192, 108))

        # CASE: keep ratio if no width given
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, size=(None, 108)))
        self.assertEqual(image.size, (192, 108))

        # CASE: size above, return original
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, size=(3000, 2000)))
        self.assertEqual(image.size, (1920, 1080))

        # CASE: same size, no change
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, size=(1920, 1080)))
        self.assertEqual(image.size, (1920, 1080))

        # CASE: no resize if above
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, size=(3000, None)))
        self.assertEqual(image.size, (1920, 1080))

        # CASE: no resize if above
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, size=(None, 2000)))
        self.assertEqual(image.size, (1920, 1080))

        # CASE: vertical image, correct resize if below
        base64_image_1080_1920 = tools.image_to_base64(PIL.Image.new('RGB', (1080, 1920)), 'PNG')
        image = tools.base64_to_image(tools.image_process(base64_image_1080_1920, size=(3000, 192)))
        self.assertEqual(image.size, (108, 192))

        # CASE: adapt to width
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, size=(192, 200)))
        self.assertEqual(image.size, (192, 108))

        # CASE: adapt to height
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, size=(400, 108)))
        self.assertEqual(image.size, (192, 108))

    def test_11_image_process(self):
        """Test that image_proces is working as expected."""
        # CASE: return base64_source if format is SVG
        res = tools.image_process(self.base64_svg)
        self.assertEqual(res, self.base64_svg)

        # CASE: size excessive
        base64_image_excessive = tools.image_to_base64(PIL.Image.new('RGB', (45001, 1000)), 'PNG')
        with self.assertRaises(ValueError):
            res = tools.image_process(base64_image_excessive, verify_resolution=True)

        # CASE: max_width
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, (192, 0)))
        self.assertEqual(image.size, (192, 108))

        # CASE: PNG RGBA doesn't apply quality, just optimize
        base64_image_1080_1920_rgba = tools.image_to_base64(PIL.Image.new('RGBA', (1080, 1920)), 'PNG')
        res = tools.image_process(base64_image_1080_1920_rgba)
        self.assertLessEqual(len(res), len(base64_image_1080_1920_rgba))

        # CASE: PNG RGB doesn't apply quality, just optimize
        base64_image_1080_1920_rgb = tools.image_to_base64(PIL.Image.new('P', (1080, 1920)), 'PNG')
        res = tools.image_process(base64_image_1080_1920_rgb)
        self.assertLessEqual(len(res), len(base64_image_1080_1920_rgb))

        # CASE: JPEG strictly reduced quality
        res = tools.image_process(self.base64_image_1920_1080)
        self.assertLessEqual(len(res), len(self.base64_image_1920_1080))

        # CASE: GIF doesn't apply quality, just optimize
        base64_image_1080_1920_gif = tools.image_to_base64(PIL.Image.new('RGB', (1080, 1920)), 'GIF')
        res = tools.image_process(base64_image_1080_1920_gif)
        self.assertLessEqual(len(res), len(base64_image_1080_1920_gif))

        # CASE: unsupported format
        base64_image_1080_1920_tiff = tools.image_to_base64(PIL.Image.new('RGB', (1080, 1920)), 'TIFF')
        image = tools.base64_to_image(tools.image_process(base64_image_1080_1920_tiff))
        self.assertEqual(image.format, 'JPEG')

    def test_12_image_process(self):
        """Test that image_process is working as expected with crop."""

        # CASE: return False if base64_source is falsy
        res = tools.image_process(False, size=(1, 1), crop='center')
        self.assertFalse(res)

        # CASE: size, crop biggest possible
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, size=(2000, 2000), crop='center'))
        self.assertEqual(image.size, (1080, 1080))

        # CASE: size vertical, limit height
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, size=(2000, 4000), crop='center'))
        self.assertEqual(image.size, (540, 1080))

        # CASE: size horizontal, limit width
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, size=(4000, 2000), crop='center'))
        self.assertEqual(image.size, (1920, 960))

        # CASE: type center
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, size=(2000, 2000), crop='center'))
        self.assertEqual(image.size, (1080, 1080))

        # CASE: type center
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, size=(2000, 2000), crop='top'))
        self.assertEqual(image.size, (1080, 1080))

        # CASE: type bottom
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, size=(2000, 2000), crop='bottom'))
        self.assertEqual(image.size, (1080, 1080))

        # CASE: wrong crop value, use center
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, size=(2000, 2000), crop='wrong'))
        self.assertEqual(image.size, (1080, 1080))

        # CASE: size given, resize too
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, size=(512, 512), crop='center'))
        self.assertEqual(image.size, (512, 512))

    def test_13_image_process_colorize(self):
        """Test that image_process is working as expected for colorize."""

        # verify initial condition
        image_rgba = PIL.Image.new('RGBA', (1, 1))
        self.assertEqual(image_rgba.getpixel((0, 0)), (0, 0, 0, 0))
        base64_rgba = tools.image_to_base64(image_rgba, 'PNG')

        # CASE: color random, color has changed
        image = tools.base64_to_image(tools.image_process(base64_rgba, colorize=True))
        self.assertNotEqual(image.getpixel((0, 0)), (0, 0, 0))

    def test_16_image_process_resize(self):
        """Test that image_process is working as expected."""

        # CASE: return input if no width or height
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080))
        self.assertEqual(image.size, (1920, 1080))

        # CASE: given width, resize and keep ratio
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, (192, 0)))
        self.assertEqual(image.size, (192, 108))

        # CASE: given height, resize and keep ratio
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, (0, 108)))
        self.assertEqual(image.size, (192, 108))

        # CASE: crop
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, (192, 108), crop=True))
        self.assertEqual(image.size, (192, 108))

        # CASE: keep ratio
        image = tools.base64_to_image(tools.image_process(self.base64_image_1920_1080, (1000, 1000)))
        self.assertEqual(image.size, (1000, 562))

    def test_17_image_data_uri(self):
        """Test that image_data_uri is working as expected."""
        self.assertEqual(tools.image_data_uri(self.base64_image_1x1), 'data:image/png;base64,' + self.base64_image_1x1.decode('ascii'))
