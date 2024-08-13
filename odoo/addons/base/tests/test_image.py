# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import binascii

from PIL import Image, ImageDraw, PngImagePlugin

from odoo import tools
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


def img_open(data):
    return Image.open(io.BytesIO(data))


class TestImage(TransactionCase):
    """Tests for the different image tools helpers."""
    def setUp(self):
        super(TestImage, self).setUp()
        self.bg_color = (135, 90, 123)
        self.fill_color = (0, 160, 157)

        self.img_1x1_png = base64.b64decode(b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC')
        self.img_svg = b'<svg></svg>'
        self.img_1920x1080_jpeg = tools.image_apply_opt(Image.new('RGB', (1920, 1080)), 'JPEG')
        # The following image contains a tag `Lens Info` with a value of `3.99mm f/1.8`
        # This particular tag 0xa432 makes the `exif_transpose` method fail in 5.4.1 < Pillow < 7.2.0
        self.img_exif_jpg = base64.b64decode(b"""/9j/4AAQSkZJRgABAQAAAQABAAD/4QDQRXhpZgAATU0AKgAAAAgABgESAAMAAAABAAYAAAEaAAUA
                                  AAABAAAAVgEbAAUAAAABAAAAXgEoAAMAAAABAAEAAAITAAMAAAABAAEAAIdpAAQAAAABAAAAZgAA
                                  AAAAAAABAAAAAQAAAAEAAAABAAWQAAAHAAAABDAyMzGRAQAHAAAABAECAwCgAAAHAAAABDAxMDCg
                                  AQADAAAAAf//AACkMgAFAAAABAAAAKgAAAAAAAABjwAAAGQAAAGPAAAAZAAAAAkAAAAFAAAACQAA
                                  AAX/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAx
                                  NDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIy
                                  MjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAADAAYDASIAAhEBAxEB/8QAHwAAAQUBAQEB
                                  AQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1Fh
                                  ByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZ
                                  WmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXG
                                  x8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAEC
                                  AwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHB
                                  CSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0
                                  dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX
                                  2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD3+iiigD//2Q==""")

        # Draw a red square in the middle of the image, this will be used to
        # verify crop is working. The border is going to be `self.bg_color` and
        # the middle is going to be `self.fill_color`.

        # horizontal image (border is left/right)
        image = Image.new('RGB', (1920, 1080), color=self.bg_color)
        offset = (image.size[0] - image.size[1]) / 2
        draw = ImageDraw.Draw(image)
        draw.rectangle(xy=[
            (offset, 0),
            (image.size[0] - offset, image.size[1])
        ], fill=self.fill_color)
        self.img_1920x1080_png = tools.image_apply_opt(image, 'PNG')

        # vertical image (border is top/bottom)
        image = Image.new('RGB', (1080, 1920), color=self.bg_color)
        offset = (image.size[1] - image.size[0]) / 2
        draw = ImageDraw.Draw(image)
        draw.rectangle(xy=[
            (0, offset),
            (image.size[0], image.size[1] - offset)
        ], fill=self.fill_color)
        self.img_1080x1920_png = tools.image_apply_opt(image, 'PNG')

    def test_00_base64_to_image(self):
        """Test that base64 is correctly opened as a PIL image."""
        image = img_open(self.img_1x1_png)
        self.assertEqual(type(image), PngImagePlugin.PngImageFile, "base64 as bytes, correct format")
        self.assertEqual(image.size, (1, 1), "base64 as bytes, correct size")

        with self.assertRaises(UserError, msg="This file could not be decoded as an image file. Please try with a different file."):
            image = tools.base64_to_image(b'oazdazpodazdpok')

        with self.assertRaises(UserError, msg="This file could not be decoded as an image file. Please try with a different file."):
            image = tools.base64_to_image(b'oazdazpodazdpokd')

    def test_01_image_to_base64(self):
        """Test that a PIL image is correctly saved as base64."""
        image = Image.new('RGB', (1, 1))
        image_base64 = tools.image_to_base64(image, 'PNG')
        self.assertEqual(image_base64, base64.b64encode(self.img_1x1_png))

    def test_02_image_fix_orientation(self):
        """Test that the orientation of images is correct."""

        # Colors that can be distinguished among themselves even with jpeg loss.
        blue = (0, 0, 255)
        yellow = (255, 255, 0)
        green = (0, 255, 0)
        pink = (255, 0, 255)
        # Image large enough so jpeg loss is not a huge factor in the corners.
        size = 50
        expected = (blue, yellow, green, pink)

        # They are all supposed to be same image: (blue, yellow, green, pink) in
        # that order, but each encoded with a different orientation.
        self._orientation_test(1, (blue, yellow, green, pink), size, expected)  # top/left
        self._orientation_test(2, (yellow, blue, pink, green), size, expected)  # top/right
        self._orientation_test(3, (pink, green, yellow, blue), size, expected)  # bottom/right
        self._orientation_test(4, (green, pink, blue, yellow), size, expected)  # bottom/left
        self._orientation_test(5, (blue, green, yellow, pink), size, expected)  # left/top
        self._orientation_test(6, (yellow, pink, blue, green), size, expected)  # right/top
        self._orientation_test(7, (pink, yellow, green, blue), size, expected)  # right/bottom
        self._orientation_test(8, (green, blue, pink, yellow), size, expected)  # left/bottom

    def test_03_image_fix_orientation_exif(self):
        """Test that a jpg image with exif orientation tag gets rotated"""
        image = img_open(self.img_exif_jpg)
        self.assertEqual(image.size, (6,3))
        image = tools.image_fix_orientation(image)
        self.assertEqual(image.size, (3,6))

    def test_10_image_process_source(self):
        """Test the source parameter of image_process."""
        self.assertFalse(tools.image_process(False), "return False if source is falsy")
        self.assertEqual(tools.image_process(self.img_svg), self.img_svg, "return source if format is SVG")

        # in the following tests, pass `quality` to force the processing
        with self.assertRaises(UserError, msg="This file could not be decoded as an image file. Please try with a different file."):
            tools.image_process(b'oazdazpodazdpokd', quality=95)

        image = img_open(tools.image_process(self.img_1920x1080_jpeg, quality=95))
        self.assertEqual(image.size, (1920, 1080), "OK return the image")

    def test_11_image_process_size(self):
        """Test the size parameter of image_process."""

        # Format of `tests`: (original image, size parameter, expected result, text)
        tests = [
            (self.img_1920x1080_jpeg, (192, 108), (192, 108), "resize to given size"),
            (self.img_1920x1080_jpeg, (1920, 1080), (1920, 1080), "same size, no change"),
            (self.img_1920x1080_jpeg, (192, None), (192, 108), "set height from ratio"),
            (self.img_1920x1080_jpeg, (0, 108), (192, 108), "set width from ratio"),
            (self.img_1920x1080_jpeg, (192, 200), (192, 108), "adapt to width"),
            (self.img_1920x1080_jpeg, (400, 108), (192, 108), "adapt to height"),
            (self.img_1920x1080_jpeg, (3000, 2000), (1920, 1080), "don't resize above original, both set"),
            (self.img_1920x1080_jpeg, (3000, False), (1920, 1080), "don't resize above original, width set"),
            (self.img_1920x1080_jpeg, (None, 2000), (1920, 1080), "don't resize above original, height set"),
            (self.img_1080x1920_png, (3000, 192), (108, 192), "vertical image, resize if below"),
        ]

        count = 0
        for test in tests:
            image = img_open(tools.image_process(test[0], size=test[1]))
            self.assertEqual(image.size, test[2], test[3])
            count = count + 1
        self.assertEqual(count, 10, "ensure the loop is ran")

    def test_12_image_process_verify_resolution(self):
        """Test the verify_resolution parameter of image_process."""
        res = tools.image_process(self.img_1920x1080_jpeg, verify_resolution=True)
        self.assertNotEqual(res, False, "size ok")
        image_excessive = tools.image_apply_opt(Image.new('RGB', (50001, 1000)), 'PNG')
        with self.assertRaises(UserError, msg="size excessive"):
            tools.image_process(image_excessive, verify_resolution=True)

    def test_13_image_process_quality(self):
        """Test the quality parameter of image_process."""

        # CASE: PNG RGBA doesn't apply quality, just optimize
        image = tools.image_apply_opt(Image.new('RGBA', (1080, 1920)), 'PNG')
        res = tools.image_process(image)
        self.assertLessEqual(len(res), len(image))

        # CASE: PNG RGB doesn't apply quality, just optimize
        image = tools.image_apply_opt(Image.new('P', (1080, 1920)), 'PNG')
        res = tools.image_process(image)
        self.assertLessEqual(len(res), len(image))

        # CASE: JPEG optimize + reduced quality
        res = tools.image_process(self.img_1920x1080_jpeg)
        self.assertLessEqual(len(res), len(self.img_1920x1080_jpeg))

        # CASE: GIF doesn't apply quality, just optimize
        image = tools.image_apply_opt(Image.new('RGB', (1080, 1920)), 'GIF')
        res = tools.image_process(image)
        self.assertLessEqual(len(res), len(image))

    def test_14_image_process_crop(self):
        """Test the crop parameter of image_process."""

        # Optimized PNG use palette, getpixel below will return palette value.
        fill = 0
        bg = 1

        # Images with small dimensions
        small_width = tools.image_apply_opt(Image.new('RGBA', (1, 16)), 'PNG')
        small_height = tools.image_apply_opt(Image.new('RGBA', (16, 1)), 'PNG')

        # Format of `tests`: (original base64 image, size parameter, crop parameter, res size, res color (top, bottom, left, right), text)
        tests = [
            (self.img_1920x1080_png, None, None, (1920, 1080), (fill, fill, bg, bg), "horizontal, verify initial"),
            (self.img_1920x1080_png, (2000, 2000), 'center', (1080, 1080), (fill, fill, fill, fill), "horizontal, crop biggest possible"),
            (self.img_1920x1080_png, (2000, 4000), 'center', (540, 1080), (fill, fill, fill, fill), "horizontal, size vertical, limit height"),
            (self.img_1920x1080_png, (4000, 2000), 'center', (1920, 960), (fill, fill, bg, bg), "horizontal, size horizontal, limit width"),
            (self.img_1920x1080_png, (512, 512), 'center', (512, 512), (fill, fill, fill, fill), "horizontal, type center"),
            (self.img_1920x1080_png, (512, 512), 'top', (512, 512), (fill, fill, fill, fill), "horizontal, type top"),
            (self.img_1920x1080_png, (512, 512), 'bottom', (512, 512), (fill, fill, fill, fill), "horizontal, type bottom"),
            (self.img_1920x1080_png, (512, 512), 'wrong', (512, 512), (fill, fill, fill, fill), "horizontal, wrong crop value, use center"),
            (self.img_1920x1080_png, (192, 0), None, (192, 108), (fill, fill, bg, bg), "horizontal, not cropped, just do resize"),
            (small_height, (25, 50), 'center', (1, 1), (fill, fill, fill, fill), "horizontal, small height, size vertical"),

            (self.img_1080x1920_png, None, None, (1080, 1920), (bg, bg, fill, fill), "vertical, verify initial"),
            (self.img_1080x1920_png, (2000, 2000), 'center', (1080, 1080), (fill, fill, fill, fill), "vertical, crop biggest possible"),
            (self.img_1080x1920_png, (2000, 4000), 'center', (960, 1920), (bg, bg, fill, fill), "vertical, size vertical, limit height"),
            (self.img_1080x1920_png, (4000, 2000), 'center', (1080, 540), (fill, fill, fill, fill), "vertical, size horizontal, limit width"),
            (self.img_1080x1920_png, (512, 512), 'center', (512, 512), (fill, fill, fill, fill), "vertical, type center"),
            (self.img_1080x1920_png, (512, 512), 'top', (512, 512), (bg, fill, fill, fill), "vertical, type top"),
            (self.img_1080x1920_png, (512, 512), 'bottom', (512, 512), (fill, bg, fill, fill), "vertical, type bottom"),
            (self.img_1080x1920_png, (512, 512), 'wrong', (512, 512), (fill, fill, fill, fill), "vertical, wrong crop value, use center"),
            (self.img_1080x1920_png, (108, 0), None, (108, 192), (bg, bg, fill, fill), "vertical, not cropped, just do resize"),
            (small_width, (50, 25), 'center', (1, 1), (fill, fill, fill, fill), "vertical, small width, size horizontal"),
        ]

        count = 0
        for test in tests:
            count = count + 1
            # process the image, pass quality to make sure the result is palette
            image = img_open(tools.image_process(test[0], size=test[1], crop=test[2], quality=95))
            # verify size
            self.assertEqual(image.size, test[3], "%s - correct size" % test[5])

            half_width, half_height = image.size[0] / 2, image.size[1] / 2
            top, bottom, left, right = 0, image.size[1] - 1, 0, image.size[0] - 1
            # verify top
            px = (half_width, top)
            self.assertEqual(image.getpixel(px), test[4][0], "%s - color top (%s, %s)" % (test[5], px[0], px[1]))
            # verify bottom
            px = (half_width, bottom)
            self.assertEqual(image.getpixel(px), test[4][1], "%s - color bottom (%s, %s)" % (test[5], px[0], px[1]))
            # verify left
            px = (left, half_height)
            self.assertEqual(image.getpixel(px), test[4][2], "%s - color left (%s, %s)" % (test[5], px[0], px[1]))
            # verify right
            px = (right, half_height)
            self.assertEqual(image.getpixel(px), test[4][3], "%s - color right (%s, %s)" % (test[5], px[0], px[1]))

        self.assertEqual(count, 2 * 10, "ensure the loop is ran")

    def test_15_image_process_colorize(self):
        """Test the colorize parameter of image_process."""

        # verify initial condition
        image_rgba = Image.new('RGBA', (1, 1))
        self.assertEqual(image_rgba.mode, 'RGBA')
        self.assertEqual(image_rgba.getpixel((0, 0)), (0, 0, 0, 0))
        rgba = tools.image_apply_opt(image_rgba, 'PNG')

        # CASE: color random, color has changed
        image = img_open(tools.image_process(rgba, colorize=True))
        self.assertEqual(image.mode, 'RGB')
        self.assertNotEqual(image.getpixel((0, 0)), (0, 0, 0))

    def test_16_image_process_format(self):
        """Test the format parameter of image_process."""

        image = img_open(tools.image_process(self.img_1920x1080_jpeg, output_format='PNG'))
        self.assertEqual(image.format, 'PNG', "change format to PNG")

        image = img_open(tools.image_process(self.img_1x1_png, output_format='JpEg'))
        self.assertEqual(image.format, 'JPEG', "change format to JPEG (case insensitive)")

        image = img_open(tools.image_process(self.img_1920x1080_jpeg, output_format='BMP'))
        self.assertEqual(image.format, 'PNG', "change format to BMP converted to PNG")

        image_1080_1920_rgba = tools.image_apply_opt(Image.new('RGBA', (108, 192)), 'PNG')
        image = img_open(tools.image_process(image_1080_1920_rgba, output_format='jpeg'))
        self.assertEqual(image.format, 'JPEG', "change format PNG with RGBA to JPEG")

        # pass quality to force the image to be processed
        image_1080_1920_tiff = tools.image_apply_opt(Image.new('RGB', (108, 192)), 'TIFF')
        image = img_open(tools.image_process(image_1080_1920_tiff, quality=95))
        self.assertEqual(image.format, 'JPEG', "unsupported format to JPEG")

    def test_20_image_data_uri(self):
        """Test that image_data_uri is working as expected."""
        self.assertEqual(tools.image_data_uri(base64.b64encode(self.img_1x1_png)), 'data:image/png;base64,' + base64.b64encode(self.img_1x1_png).decode('ascii'))

    def test_21_image_guess_size_from_field_name(self):
        f = tools.image_guess_size_from_field_name
        # Test case: empty field_name input
        self.assertEqual(f(''), (0, 0))
        # Test case: custom field_name input
        self.assertEqual(f('custom_field'), (0, 0))
        # Test case: field_name input that starts with 'x_'
        self.assertEqual(f('x_field'), (0, 0))
        # Test case: field_name input that starts with 'x_' and ends with a number less than 16
        self.assertEqual(f('x_studio_image_1'), (0, 0))
        # Test case: field_name input that starts with 'x_' and ends with a number greater than 16
        self.assertEqual(f('x_studio_image_32'), (0, 0))
        # Test case: field_name input that has a suffix less than 16
        self.assertEqual(f('image_15'), (0, 0))
        # Test case: field_name input that has a suffix equal to 16
        self.assertEqual(f('image_16'), (16, 16))
        # Test case: field_name input that has a suffix greater than 16
        self.assertEqual(f('image_32'), (32, 32))
        # Test case: field_name input that has a suffix with 2 numbers
        self.assertEqual(f('image_1920_1080'), (1080, 1080))
        # Test case: field_name input that has a float as suffix
        self.assertEqual(f('image_32.5'), (0, 0))
        # Test case: field_name input that has a suffix greater than 16 but no underscore
        self.assertEqual(f('image32'), (0, 0))

    def _assertAlmostEqualSequence(self, rgb1, rgb2, delta=10):
        self.assertEqual(len(rgb1), len(rgb2))
        for index, t in enumerate(zip(rgb1, rgb2)):
            self.assertAlmostEqual(t[0], t[1], delta=delta, msg="%s vs %s at %d" % (rgb1, rgb2, index))

    def _get_exif_colored_square(self, orientation, colors, size):
        image = Image.new('RGB', (size, size), color=self.bg_color)
        draw = ImageDraw.Draw(image)
        # Paint the colors on the 4 corners, to be able to test which colors
        # move on which corners.
        draw.rectangle(xy=[(0, 0), (size // 2, size // 2)], fill=colors[0])        # top/left
        draw.rectangle(xy=[(size // 2, 0), (size, size // 2)], fill=colors[1])     # top/right
        draw.rectangle(xy=[(0, size // 2), (size // 2, size)], fill=colors[2])     # bottom/left
        draw.rectangle(xy=[(size // 2, size // 2), (size, size)], fill=colors[3])  # bottom/right
        # Set the proper exif tag based on orientation params.
        exif = b'Exif\x00\x00II*\x00\x08\x00\x00\x00\x01\x00\x12\x01\x03\x00\x01\x00\x00\x00' + bytes([orientation]) + b'\x00\x00\x00\x00\x00\x00\x00'
        # The image image is saved with the exif tag.
        return tools.image_apply_opt(image, 'JPEG', exif=exif)

    def _orientation_test(self, orientation, colors, size, expected):
        # Generate the test image based on orientation and order of colors.
        image = self._get_exif_colored_square(orientation, colors, size)
        # The image is read again now that it has orientation added.
        fixed_image = tools.image_fix_orientation(img_open(image))
        # Ensure colors are in the right order (blue, yellow, green, pink).
        self._assertAlmostEqualSequence(fixed_image.getpixel((0, 0)), expected[0])                # top/left
        self._assertAlmostEqualSequence(fixed_image.getpixel((size - 1, 0)), expected[1])         # top/right
        self._assertAlmostEqualSequence(fixed_image.getpixel((0, size - 1)), expected[2])         # bottom/left
        self._assertAlmostEqualSequence(fixed_image.getpixel((size - 1, size - 1)), expected[3])  # bottom/right

    def test_ptype_image_to_jpeg(self):
        """converts to RGB when saving as JPEG"""
        image1 = Image.new('P', (1, 1), color='red')
        image2 = Image.new('RGB', (1, 1), color='red')
        self.assertEqual(tools.image.image_apply_opt(image1, 'JPEG'), tools.image.image_apply_opt(image2, 'JPEG'))
