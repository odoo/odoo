import io
import os
import sys
import unittest
import warnings
from tempfile import mkdtemp
from unittest import mock

try:
    import pymaging_png  # ensure that PNG support is installed
    import qrcode.image.pure
except ImportError:  # pragma: no cover
    pymaging_png = None

import qrcode
import qrcode.image.svg
import qrcode.util
from qrcode.exceptions import DataOverflowError
from qrcode.image.base import BaseImage
from qrcode.image.pil import Image as pil_Image
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles import colormasks, moduledrawers
from qrcode.tests.svg import SvgImageWhite
from qrcode.util import MODE_8BIT_BYTE, MODE_ALPHA_NUM, MODE_NUMBER, QRData

UNICODE_TEXT = '\u03b1\u03b2\u03b3'
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)


class QRCodeTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = mkdtemp()

    def tearDown(self):
        os.rmdir(self.tmpdir)

    def test_basic(self):
        qr = qrcode.QRCode(version=1)
        qr.add_data('a')
        qr.make(fit=False)

    def test_large(self):
        qr = qrcode.QRCode(version=27)
        qr.add_data('a')
        qr.make(fit=False)

    def test_invalid_version(self):
        qr = qrcode.QRCode(version=41)
        self.assertRaises(ValueError, qr.make, fit=False)

    def test_invalid_border(self):
        self.assertRaises(ValueError, qrcode.QRCode, border=-1)

    def test_overflow(self):
        qr = qrcode.QRCode(version=1)
        qr.add_data('abcdefghijklmno')
        self.assertRaises(DataOverflowError, qr.make, fit=False)

    def test_add_qrdata(self):
        qr = qrcode.QRCode(version=1)
        data = QRData('a')
        qr.add_data(data)
        qr.make(fit=False)

    def test_fit(self):
        qr = qrcode.QRCode()
        qr.add_data('a')
        qr.make()
        self.assertEqual(qr.version, 1)
        qr.add_data('bcdefghijklmno')
        qr.make()
        self.assertEqual(qr.version, 2)

    def test_mode_number(self):
        qr = qrcode.QRCode()
        qr.add_data('1234567890123456789012345678901234', optimize=0)
        qr.make()
        self.assertEqual(qr.version, 1)
        self.assertEqual(qr.data_list[0].mode, MODE_NUMBER)

    def test_mode_alpha(self):
        qr = qrcode.QRCode()
        qr.add_data('ABCDEFGHIJ1234567890', optimize=0)
        qr.make()
        self.assertEqual(qr.version, 1)
        self.assertEqual(qr.data_list[0].mode, MODE_ALPHA_NUM)

    def test_regression_mode_comma(self):
        qr = qrcode.QRCode()
        qr.add_data(',', optimize=0)
        qr.make()
        self.assertEqual(qr.data_list[0].mode, MODE_8BIT_BYTE)

    def test_mode_8bit(self):
        qr = qrcode.QRCode()
        qr.add_data('abcABC' + UNICODE_TEXT, optimize=0)
        qr.make()
        self.assertEqual(qr.version, 1)
        self.assertEqual(qr.data_list[0].mode, MODE_8BIT_BYTE)

    def test_mode_8bit_newline(self):
        qr = qrcode.QRCode()
        qr.add_data('ABCDEFGHIJ1234567890\n', optimize=0)
        qr.make()
        self.assertEqual(qr.data_list[0].mode, MODE_8BIT_BYTE)

    def test_render_pil(self):
        qr = qrcode.QRCode()
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image()
        img.save(io.BytesIO())
        self.assertIsInstance(img.get_image(), pil_Image.Image)

    def test_render_pil_with_transparent_background(self):
        qr = qrcode.QRCode()
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(back_color='TransParent')
        img.save(io.BytesIO())

    def test_render_pil_with_red_background(self):
        qr = qrcode.QRCode()
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(back_color='red')
        img.save(io.BytesIO())

    def test_render_pil_with_rgb_color_tuples(self):
        qr = qrcode.QRCode()
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(back_color=(255, 195, 235), fill_color=(55, 95, 35))
        img.save(io.BytesIO())

    def test_render_with_pattern(self):
        qr = qrcode.QRCode(mask_pattern=3)
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image()
        img.save(io.BytesIO())

    def test_make_image_with_wrong_pattern(self):
        with self.assertRaises(TypeError):
            qrcode.QRCode(mask_pattern='string pattern')

        with self.assertRaises(ValueError):
            qrcode.QRCode(mask_pattern=-1)

        with self.assertRaises(ValueError):
            qrcode.QRCode(mask_pattern=42)

    def test_mask_pattern_setter(self):
        qr = qrcode.QRCode()

        with self.assertRaises(TypeError):
            qr.mask_pattern = "string pattern"

        with self.assertRaises(ValueError):
            qr.mask_pattern = -1

        with self.assertRaises(ValueError):
            qr.mask_pattern = 8

    def test_qrcode_bad_factory(self):
        with self.assertRaises(TypeError):
           qrcode.QRCode(image_factory='not_BaseImage')

        with self.assertRaises(AssertionError):
            qrcode.QRCode(image_factory=dict)

    def test_qrcode_factory(self):

        class MockFactory(BaseImage):
            drawrect = mock.Mock()
            new_image = mock.Mock()

        qr = qrcode.QRCode(image_factory=MockFactory)
        qr.add_data(UNICODE_TEXT)
        qr.make_image()
        self.assertTrue(MockFactory.new_image.called)
        self.assertTrue(MockFactory.drawrect.called)

    def test_render_svg(self):
        qr = qrcode.QRCode()
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=qrcode.image.svg.SvgImage)
        img.save(io.BytesIO())

    def test_render_svg_path(self):
        qr = qrcode.QRCode()
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
        img.save(io.BytesIO())

    def test_render_svg_fragment(self):
        qr = qrcode.QRCode()
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=qrcode.image.svg.SvgFragmentImage)
        img.save(io.BytesIO())

    def test_svg_string(self):
        qr = qrcode.QRCode()
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=qrcode.image.svg.SvgFragmentImage)
        file_like = io.BytesIO()
        img.save(file_like)
        file_like.seek(0)
        assert file_like.read() in img.to_string()

    def test_render_svg_with_background(self):
        qr = qrcode.QRCode()
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=SvgImageWhite)
        img.save(io.BytesIO())

    @unittest.skipIf(not pymaging_png, "Requires pymaging with PNG support")
    def test_render_pymaging_png(self):
        qr = qrcode.QRCode()
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=qrcode.image.pure.PymagingImage)
        from pymaging import Image as pymaging_Image
        self.assertIsInstance(img.get_image(), pymaging_Image)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', DeprecationWarning)
            img.save(io.BytesIO())

    @unittest.skipIf(not pymaging_png, "Requires pymaging")
    def test_render_pymaging_png_bad_kind(self):
        qr = qrcode.QRCode()
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=qrcode.image.pure.PymagingImage)
        with self.assertRaises(ValueError):
            img.save(io.BytesIO(), kind='FISH')

    def test_render_styled_pil_image(self):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=StyledPilImage)
        img.save(io.BytesIO())

    def test_render_styled_with_embeded_image(self):
        embeded_img = pil_Image.new('RGB', (10, 10), color='red')
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=StyledPilImage, embeded_image=embeded_img)
        img.save(io.BytesIO())

    def test_render_styled_with_embeded_image_path(self):
        tmpfile = os.path.join(self.tmpdir, "test.png")
        embeded_img = pil_Image.new('RGB', (10, 10), color='red')
        embeded_img.save(tmpfile)
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=StyledPilImage, embeded_image_path=tmpfile)
        img.save(io.BytesIO())
        os.remove(tmpfile)

    def test_render_styled_with_square_module_drawer(self):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=StyledPilImage, module_drawer=moduledrawers.SquareModuleDrawer())
        img.save(io.BytesIO())

    def test_render_styled_with_gapped_module_drawer(self):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=StyledPilImage, module_drawer=moduledrawers.GappedSquareModuleDrawer())
        img.save(io.BytesIO())

    def test_render_styled_with_circle_module_drawer(self):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=StyledPilImage, module_drawer=moduledrawers.CircleModuleDrawer())
        img.save(io.BytesIO())

    def test_render_styled_with_rounded_module_drawer(self):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=StyledPilImage, module_drawer=moduledrawers.RoundedModuleDrawer())
        img.save(io.BytesIO())

    def test_render_styled_with_vertical_bars_module_drawer(self):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=StyledPilImage, module_drawer=moduledrawers.VerticalBarsDrawer())
        img.save(io.BytesIO())

    def test_render_styled_with_horizontal_bars_module_drawer(self):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(UNICODE_TEXT)
        img = qr.make_image(image_factory=StyledPilImage, module_drawer=moduledrawers.HorizontalBarsDrawer())
        img.save(io.BytesIO())

    def test_render_styled_with_default_solid_color_mask(self):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(UNICODE_TEXT)
        mask = colormasks.SolidFillColorMask()
        img = qr.make_image(image_factory=StyledPilImage, color_mask=mask)
        img.save(io.BytesIO())

    def test_render_styled_with_solid_color_mask(self):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(UNICODE_TEXT)
        mask = colormasks.SolidFillColorMask(back_color=WHITE, front_color=RED)
        img = qr.make_image(image_factory=StyledPilImage, color_mask=mask)
        img.save(io.BytesIO())

    def test_render_styled_with_color_mask_with_transparency(self):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(UNICODE_TEXT)
        mask = colormasks.SolidFillColorMask(back_color=(255, 0, 255, 255), front_color=RED)
        img = qr.make_image(image_factory=StyledPilImage, color_mask=mask)
        img.save(io.BytesIO())
        assert img.mode == "RGBA"

    def test_render_styled_with_radial_gradient_color_mask(self):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(UNICODE_TEXT)
        mask = colormasks.RadialGradiantColorMask(back_color=WHITE, center_color=BLACK, edge_color=RED)
        img = qr.make_image(image_factory=StyledPilImage, color_mask=mask)
        img.save(io.BytesIO())

    def test_render_styled_with_square_gradient_color_mask(self):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(UNICODE_TEXT)
        mask = colormasks.SquareGradiantColorMask(back_color=WHITE, center_color=BLACK, edge_color=RED)
        img = qr.make_image(image_factory=StyledPilImage, color_mask=mask)
        img.save(io.BytesIO())

    def test_render_styled_with_horizontal_gradient_color_mask(self):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(UNICODE_TEXT)
        mask = colormasks.HorizontalGradiantColorMask(back_color=WHITE, left_color=RED, right_color=BLACK)
        img = qr.make_image(image_factory=StyledPilImage, color_mask=mask)
        img.save(io.BytesIO())

    def test_render_styled_with_vertical_gradient_color_mask(self):
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(UNICODE_TEXT)
        mask = colormasks.VerticalGradiantColorMask(back_color=WHITE, top_color=RED, bottom_color=BLACK)
        img = qr.make_image(image_factory=StyledPilImage, color_mask=mask)
        img.save(io.BytesIO())

    def test_render_styled_with_image_color_mask(self):
        img_mask = pil_Image.new('RGB', (10, 10), color='red')
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
        qr.add_data(UNICODE_TEXT)
        mask = colormasks.ImageColorMask(back_color=WHITE, color_mask_image=img_mask)
        img = qr.make_image(image_factory=StyledPilImage, color_mask=mask)
        img.save(io.BytesIO())

    def test_optimize(self):
        qr = qrcode.QRCode()
        text = 'A1abc12345def1HELLOa'
        qr.add_data(text, optimize=4)
        qr.make()
        self.assertEqual(
            [d.mode for d in qr.data_list],
            [
                MODE_8BIT_BYTE, MODE_NUMBER, MODE_8BIT_BYTE, MODE_ALPHA_NUM,
                MODE_8BIT_BYTE
            ]
        )
        self.assertEqual(qr.version, 2)

    def test_optimize_short(self):
        qr = qrcode.QRCode()
        text = 'A1abc1234567def1HELLOa'
        qr.add_data(text, optimize=7)
        qr.make()
        self.assertEqual(len(qr.data_list), 3)
        self.assertEqual(
            [d.mode for d in qr.data_list],
            [MODE_8BIT_BYTE, MODE_NUMBER, MODE_8BIT_BYTE]
        )
        self.assertEqual(qr.version, 2)

    def test_optimize_longer_than_data(self):
        qr = qrcode.QRCode()
        text = 'ABCDEFGHIJK'
        qr.add_data(text, optimize=12)
        self.assertEqual(len(qr.data_list), 1)
        self.assertEqual(qr.data_list[0].mode, MODE_ALPHA_NUM)

    def test_optimize_size(self):
        text = 'A1abc12345123451234512345def1HELLOHELLOHELLOHELLOa' * 5

        qr = qrcode.QRCode()
        qr.add_data(text)
        qr.make()
        self.assertEqual(qr.version, 10)

        qr = qrcode.QRCode()
        qr.add_data(text, optimize=0)
        qr.make()
        self.assertEqual(qr.version, 11)

    def test_qrdata_repr(self):
        data = b'hello'
        data_obj = qrcode.util.QRData(data)
        self.assertEqual(repr(data_obj), repr(data))

    def test_print_ascii_stdout(self):
        qr = qrcode.QRCode()
        stdout_encoding = sys.stdout.encoding
        with mock.patch('sys.stdout') as fake_stdout:
            # Python 2.6 needs sys.stdout.encoding to be a real string.
            sys.stdout.encoding = stdout_encoding
            fake_stdout.isatty.return_value = None
            self.assertRaises(OSError, qr.print_ascii, tty=True)
            self.assertTrue(fake_stdout.isatty.called)

    def test_print_ascii(self):
        qr = qrcode.QRCode(border=0)
        f = io.StringIO()
        qr.print_ascii(out=f)
        printed = f.getvalue()
        f.close()
        expected = '\u2588\u2580\u2580\u2580\u2580\u2580\u2588'
        self.assertEqual(printed[:len(expected)], expected)

        f = io.StringIO()
        f.isatty = lambda: True
        qr.print_ascii(out=f, tty=True)
        printed = f.getvalue()
        f.close()
        expected = (
            '\x1b[48;5;232m\x1b[38;5;255m' +
            '\xa0\u2584\u2584\u2584\u2584\u2584\xa0')
        self.assertEqual(printed[:len(expected)], expected)

    def test_print_tty_stdout(self):
        qr = qrcode.QRCode()
        with mock.patch('sys.stdout') as fake_stdout:
            fake_stdout.isatty.return_value = None
            self.assertRaises(OSError, qr.print_tty)
            self.assertTrue(fake_stdout.isatty.called)

    def test_print_tty(self):
        qr = qrcode.QRCode()
        f = io.StringIO()
        f.isatty = lambda: True
        qr.print_tty(out=f)
        printed = f.getvalue()
        f.close()
        BOLD_WHITE_BG = '\x1b[1;47m'
        BLACK_BG = '\x1b[40m'
        WHITE_BLOCK = BOLD_WHITE_BG + '  ' + BLACK_BG
        EOL = '\x1b[0m\n'
        expected = (
            BOLD_WHITE_BG + '  '*23 + EOL +
            WHITE_BLOCK + '  '*7 + WHITE_BLOCK)
        self.assertEqual(printed[:len(expected)], expected)

    def test_get_matrix(self):
        qr = qrcode.QRCode(border=0)
        qr.add_data('1')
        self.assertEqual(qr.get_matrix(), qr.modules)

    def test_get_matrix_border(self):
        qr = qrcode.QRCode(border=1)
        qr.add_data('1')
        matrix = [row[1:-1] for row in qr.get_matrix()[1:-1]]
        self.assertEqual(matrix, qr.modules)

    def test_negative_size_at_construction(self):
        self.assertRaises(ValueError, qrcode.QRCode, box_size=-1)

    def test_negative_size_at_usage(self):
        qr = qrcode.QRCode()
        qr.box_size = -1
        self.assertRaises(ValueError, qr.make_image)


class ShortcutTest(unittest.TestCase):

    def runTest(self):
        qrcode.make('image')
