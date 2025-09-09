
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from io import BytesIO
from PIL import Image

from odoo.tests.common import HttpCase, tagged
from odoo.tools.misc import file_open


@tagged("-at_install", "post_install")
class TestFontToImg(HttpCase):

    def test_font_to_img(self):
        # This test was introduced because the play button was cropped in noble following some adaptation.
        # This test is able to reproduce the issue and ensure that the expected result is the right one
        # comparing image is not ideal, but this should work in most case, maybe adapted if the font is changed.

        response = self.url_open(
            "/mail/font_to_img/61802/rgb(0,143,140)/rgb(255,255,255)/190x200"
        )

        img = Image.open(BytesIO(response.content))
        self.assertEqual(
            img.size,
            (201, 200),
            "Looks strange regarding request but this is the current result",
        )
        # Image is a play button
        img_reference = Image.open(file_open("mail/tests/play.png", "rb"))
        self.assertEqual(img, img_reference, "Result image should be the play button")
