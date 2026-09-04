
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from PIL import ImageChops

from odoo.tests.common import HttpCase
from odoo.tools.image import binary_to_image
from odoo.tools.misc import file_open

from odoo.addons.html_editor.controllers.icons import ICONS


class TestFontToImg(HttpCase):

    def test_font_to_img(self):
        # This test was introduced because the play button was cropped in noble following some adaptation.
        # This test is able to reproduce the issue and ensure that the expected result is the right one
        # comparing image is not ideal, but this should work in most case, maybe adapted if the font is changed.

        response = self.url_open(
            "/mail/font_to_img/61802/rgb(0,143,140)/rgb(255,255,255)/190x200"
        )

        img = binary_to_image(response.content)
        self.assertEqual(
            img.size,
            (190, 200),
        )
        # Image is a play button
        img_reference = binary_to_image(file_open("mail/tests/play.png", "rb").read())
        self.assertEqual(img, img_reference,
                         "Result image should be the play button")


class TestMaterialSymbolsToImg(HttpCase):
    """
    The Material Symbols are reached by codepoint alone in `export_icon_to_png`;
    a wrong codepoint silently renders nothing at all.
    """
    # Icons chosen to cover different codepoints range and fill variants.
    TEST_ICONS = ('home', 'blind', 'stethoscope',
                  'horizontal_align_left', 'phone_cancel')

    def _render_icon(self, icon, fill=0):
        response = self.url_open(
            f'/mail/font_to_img/{icon}/oi/{fill}/000000ff/00000000/64x64fs64',
        )
        self.assertEqual(response.status_code, 200)
        return binary_to_image(response.content)

    def test_codepoints_render(self):
        for icon in self.TEST_ICONS:
            for fill in (0, 1):
                with self.subTest(icon=icon, fill=fill):
                    image = self._render_icon(icon, fill)
                    self.assertIsNotNone(
                        image.getchannel('A').getbbox(),
                        f"{icon!r} (fill={fill}) rendered a blank image",
                    )

    def test_fill_variants(self):
        for icon in self.TEST_ICONS:
            with self.subTest(icon=icon):
                outlined = self._render_icon(icon, fill=0)
                filled = self._render_icon(icon, fill=1)
                self.assertEqual(outlined.size, filled.size)
                differs = ImageChops.difference(
                    outlined, filled).getbbox() is not None
                self.assertEqual(
                    differs,
                    ICONS[icon]['has_fill'],
                    f"{icon!r} filled form should{'' if ICONS[icon]['has_fill'] else ' not'} "
                    "differ from its outlined one",
                )
