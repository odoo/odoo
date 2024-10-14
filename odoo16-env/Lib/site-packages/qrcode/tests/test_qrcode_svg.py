import io

import qrcode
from qrcode.image import svg
from qrcode.tests.consts import UNICODE_TEXT


class SvgImageWhite(svg.SvgImage):
    background = "white"


def test_render_svg():
    qr = qrcode.QRCode()
    qr.add_data(UNICODE_TEXT)
    img = qr.make_image(image_factory=svg.SvgImage)
    img.save(io.BytesIO())


def test_render_svg_path():
    qr = qrcode.QRCode()
    qr.add_data(UNICODE_TEXT)
    img = qr.make_image(image_factory=svg.SvgPathImage)
    img.save(io.BytesIO())


def test_render_svg_fragment():
    qr = qrcode.QRCode()
    qr.add_data(UNICODE_TEXT)
    img = qr.make_image(image_factory=svg.SvgFragmentImage)
    img.save(io.BytesIO())


def test_svg_string():
    qr = qrcode.QRCode()
    qr.add_data(UNICODE_TEXT)
    img = qr.make_image(image_factory=svg.SvgFragmentImage)
    file_like = io.BytesIO()
    img.save(file_like)
    file_like.seek(0)
    assert file_like.read() in img.to_string()


def test_render_svg_with_background():
    qr = qrcode.QRCode()
    qr.add_data(UNICODE_TEXT)
    img = qr.make_image(image_factory=SvgImageWhite)
    img.save(io.BytesIO())


def test_svg_circle_drawer():
    qr = qrcode.QRCode()
    qr.add_data(UNICODE_TEXT)
    img = qr.make_image(image_factory=svg.SvgPathImage, module_drawer="circle")
    img.save(io.BytesIO())
