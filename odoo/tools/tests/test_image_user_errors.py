import base64
import io
import unittest

from PIL import Image

from odoo.exceptions import UserError
from odoo.tools.image import (
    ImageProcess,
    base64_to_image,
    binary_to_image,
    image_process,
)


def _bomb() -> bytes:
    buffer = io.BytesIO()
    Image.new("1", (20000, 20000)).save(buffer, format="PNG")
    return buffer.getvalue()


class TestImageWrappersSpeakUserError(unittest.TestCase):
    bomb: bytes

    @classmethod
    def setUpClass(cls):
        cls.bomb = _bomb()

    def test_a_decompression_bomb_is_a_user_error_everywhere(self):
        for name, call in (
            ("binary_to_image", lambda: binary_to_image(self.bomb)),
            ("base64_to_image", lambda: base64_to_image(base64.b64encode(self.bomb))),
            ("ImageProcess", lambda: ImageProcess(self.bomb)),
        ):
            with self.subTest(name), self.assertRaises(UserError) as caught:
                call()
            self.assertIn("Too large image", str(caught.exception))

    def test_undecodable_bytes_are_a_user_error(self):
        for call in (
            lambda: binary_to_image(b"not an image"),
            lambda: ImageProcess(b"not an image"),
        ):
            with self.subTest(call=call), self.assertRaises(UserError) as caught:
                call()
            self.assertIn("could not be decoded", str(caught.exception))

    def test_a_truncated_image_is_a_user_error_when_its_pixels_are_needed(self):
        stream = io.BytesIO()
        Image.new("RGB", (64, 64), (1, 2, 3)).save(stream, "JPEG")
        truncated = stream.getvalue()[:-40]
        for call in (
            lambda: image_process(truncated, size=(16, 16)),
            lambda: ImageProcess(truncated).resize(16, 16),
            lambda: ImageProcess(truncated).validate(),
            lambda: image_process(truncated, size=(128, 128), verify_resolution=True),
            lambda: image_process(truncated, verify_resolution=True),
        ):
            with self.subTest(call=call), self.assertRaises(UserError) as caught:
                call()
            self.assertIn("could not be decoded", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
