import io
import os
import unittest
from tempfile import mkdtemp

import qrcode
from qrcode.image import svg

UNICODE_TEXT = "\u03b1\u03b2\u03b3"


class SvgImageWhite(svg.SvgImage):
    background = "white"


class QRCodeSvgTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = mkdtemp()

    def tearDown(self):
        os.rmdir(self.tmpdir)

    def test_render_svg(self):
        qr = qrcode.QRCode()
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=svg.SvgImage)
        img.save(io.BytesIO())

    def test_render_svg_path(self):
        qr = qrcode.QRCode()
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=svg.SvgPathImage)
        img.save(io.BytesIO())

    def test_render_svg_fragment(self):
        qr = qrcode.QRCode()
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=svg.SvgFragmentImage)
        img.save(io.BytesIO())

    def test_svg_string(self):
        qr = qrcode.QRCode()
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=svg.SvgFragmentImage)
        file_like = io.BytesIO()
        img.save(file_like)
        file_like.seek(0)
        assert file_like.read() in img.to_string()

    def test_render_svg_with_background(self):
        qr = qrcode.QRCode()
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=SvgImageWhite)
        img.save(io.BytesIO())

    def test_svg_circle_drawer(self):
        qr = qrcode.QRCode()
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=svg.SvgPathImage, module_drawer="circle")
        img.save(io.BytesIO())
