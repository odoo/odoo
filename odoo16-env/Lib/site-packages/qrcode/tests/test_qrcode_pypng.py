import io
from unittest import mock

import pytest


import qrcode
import qrcode.util
from qrcode.image.pure import PyPNGImage
from qrcode.tests.consts import UNICODE_TEXT

png = pytest.importorskip("png", reason="png is not installed")


def test_render_pypng():
    qr = qrcode.QRCode()
    qr.add_data(UNICODE_TEXT)
    img = qr.make_image(image_factory=PyPNGImage)
    assert isinstance(img.get_image(), png.Writer)

    print(img.width, img.box_size, img.border)
    img.save(io.BytesIO())


def test_render_pypng_to_str():
    qr = qrcode.QRCode()
    qr.add_data(UNICODE_TEXT)
    img = qr.make_image(image_factory=PyPNGImage)
    assert isinstance(img.get_image(), png.Writer)

    mock_open = mock.mock_open()
    with mock.patch("qrcode.image.pure.open", mock_open, create=True):
        img.save("test_file.png")
    mock_open.assert_called_once_with("test_file.png", "wb")
    mock_open("test_file.png", "wb").write.assert_called()
