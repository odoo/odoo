import base64
import io
import unittest

from PIL import Image

from odoo.exceptions import UserError
from odoo.tools.image import ImageProcess, base64_to_image, binary_to_image


def _bomb() -> bytes:
    buffer = io.BytesIO()
    Image.new("1", (20000, 20000)).save(buffer, format="PNG")
    return buffer.getvalue()


class TestImageWrappersSpeakUserError(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
