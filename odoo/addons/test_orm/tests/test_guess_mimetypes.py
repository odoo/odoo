import os.path
import unittest

from odoo.tests import tagged, BaseCase
from odoo.tools.mimetypes import _odoo_guess_mimetype, fix_filename_extension, get_extension, guess_mimetype
from odoo.tools.misc import file_open


def contents(extension):
    with file_open(os.path.join(
        os.path.dirname(__file__),
        'testfiles',
        f'case.{extension}'
    ), 'rb') as f:
        return f.read()


class MimeGuessingCases:
    allow_inherited_tests_method = True
    guess_mimetype: callable

    def test_doc(self):
        self.assertEqual(
            self.guess_mimetype(contents('doc')),
            'application/msword',
        )

    def test_xls(self):
        self.assertEqual(
            self.guess_mimetype(contents('xls')),
            'application/vnd.ms-excel',
        )

    def test_docx(self):
        self.assertEqual(
            self.guess_mimetype(contents('docx')),
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )

    def test_xlsx(self):
        self.assertEqual(
            self.guess_mimetype(contents('xlsx')),
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def test_xlsx_2025(self):
        self.assertEqual(
            guess_mimetype(contents('2025.xlsx')),
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def test_odt(self):
        self.assertEqual(
            self.guess_mimetype(contents('odt')),
            'application/vnd.oasis.opendocument.text',
        )

    def test_ods(self):
        self.assertEqual(
            self.guess_mimetype(contents('ods')),
            'application/vnd.oasis.opendocument.spreadsheet',
        )

    def test_zip(self):
        self.assertEqual(
            self.guess_mimetype(contents('zip')),
            'application/zip',
        )

    def test_gif(self):
        self.assertEqual(
            self.guess_mimetype(contents('gif')),
            'image/gif',
        )

    def test_jpeg(self):
        self.assertEqual(
            self.guess_mimetype(contents('jpg')),
            'image/jpeg',
        )

    def test_text(self):
        self.assertEqual(
            self.guess_mimetype(b"Some text with no special format.\n"),
            'text/plain',
        )

    def test_unknown(self):
        self.assertEqual(
            self.guess_mimetype(b"\1\2\3\1\2\3\1\2\3\1\2\3\1\2\3"),
            'application/octet-stream',
        )

    def test_ppt(self):
        self.assertEqual(
            self.guess_mimetype(contents('ppt')),
            'application/vnd.ms-powerpoint',
        )

    def test_pptx(self):
        self.assertEqual(
            self.guess_mimetype(contents('pptx')),
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        )

    def test_pdf(self):
        self.assertEqual(
            self.guess_mimetype(contents("pdf")),
            "application/pdf",
        )

    def test_ico(self):
        self.assertEqual(
            self.guess_mimetype(contents("ico")),
            "image/vnd.microsoft.icon",
        )

    def test_webp(self):
        self.assertEqual(
            self.guess_mimetype(contents('webp')),
            'image/webp',
        )

    def test_xml(self):
        self.assertEqual(
            self.guess_mimetype(contents('xml')),
            'text/xml',
        )

    def test_png(self):
        self.assertEqual(
            self.guess_mimetype(contents('png')),
            'image/png',
        )

    def test_bmp(self):
        # mimetype should match image/bmp, image/x-ms-bmp, ...
        # r'image/.*\bbmp'
        self.assertEqual(
            self.guess_mimetype(contents('bmp')),
            'image/bmp',
        )

    def test_svg(self):
        self.assertEqual(
            self.guess_mimetype(contents('svg')),
            'image/svg+xml',
        )

    def test_namespaced_svg(self):
        self.assertEqual(
            self.guess_mimetype(contents('namespaced.svg')),
            'image/svg+xml',
        )

    def test_empty(self):
        self.assertEqual(
            self.guess_mimetype(b''),
            'application/x-empty',
        )

    def test_mimetype_octet_stream(self):
        self.assertEqual(
            self.guess_mimetype(b'\0'),
            "application/octet-stream",
        )

    def test_whitespace_svg(self):
        # TODO
        # Tests that whitespace padded SVG are not detected as SVG in odoo implementation
        # if not magic:
        #     mimetype = guess_mimetype(b"   " + content, default='test')
        #     self.assertNotIn("svg", mimetype)
        pass

    def test_default_mimetype_empty(self):
        self.assertEqual(
            self.guess_mimetype(b"""Hello world!"""),
            'text/plain',
       )

@tagged('at_install', '-post_install')  # LEGACY at_install
class TestMimeGuessingOdoo(BaseCase, MimeGuessingCases):
    guess_mimetype = staticmethod(_odoo_guess_mimetype)

    def test_csv(self):
        self.assertEqual(
            self.guess_mimetype(contents('csv')),
            'text/plain',
        )

    def test_default(self):
        self.assertEqual(
            self.guess_mimetype(b"\1\2\3\1\2\3\1\2\3\1\2\3\1\2\3", default='test'),
            'test',
        )

@unittest.skipIf(guess_mimetype is _odoo_guess_mimetype, "python-magic not installed")
@tagged('at_install', '-post_install')  # LEGACY at_install
class TestMimeGuessingMagic(BaseCase, MimeGuessingCases):
    guess_mimetype = staticmethod(guess_mimetype)

    def test_csv(self):
        self.assertEqual(
            self.guess_mimetype(contents('csv')),
            'text/csv',
        )

    def test_default(self):
        self.assertEqual(
            self.guess_mimetype(b"", default='test'),
            "application/x-empty",
        )

@tagged('at_install', '-post_install')  # LEGACY at_install
class test_guess_mimetype(BaseCase):
    def test_mimetype_get_extension(self):
        self.assertEqual(get_extension('filename.Abc'), '.abc')
        self.assertEqual(get_extension('filename.scss'), '.scss')
        self.assertEqual(get_extension('filename.torrent'), '.torrent')
        self.assertEqual(get_extension('filename.ab_c'), '.ab_c')
        self.assertEqual(get_extension('.htaccess'), '')
        # enough to suppose that extension is present and don't suffix the filename
        self.assertEqual(get_extension('filename.tar.gz'), '.gz')
        self.assertEqual(get_extension('filename'), '')
        self.assertEqual(get_extension('filename.'), '')
        self.assertEqual(get_extension('filename.not_alnum'), '')
        self.assertEqual(get_extension('filename.with space'), '')
        self.assertEqual(get_extension('filename.notAnExtension'), '')

    def test_mimetype_fix_extension(self):
        fix = fix_filename_extension
        self.assertEqual(fix('words.txt', 'text/plain'), 'words.txt')
        self.assertEqual(fix('image.jpg', 'image/jpeg'), 'image.jpg')
        self.assertEqual(fix('image.jpeg', 'image/jpeg'), 'image.jpeg')
        self.assertEqual(fix('sheet.xls', 'application/vnd.ms-excel'), 'sheet.xls')
        self.assertEqual(fix('sheet.xls', 'application/CDFV2'), 'sheet.xls')
        xlsx_mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        self.assertEqual(fix('sheet.xlsx', xlsx_mime), 'sheet.xlsx')
        self.assertEqual(fix('sheet.xlsx', 'application/zip'), 'sheet.xlsx')
        with self.assertLogs('odoo.tools.mimetypes', 'WARNING') as capture:
            self.assertEqual(fix('image.txt', 'image/jpeg'), 'image.txt.jpg')
            self.assertEqual(fix('words.jpg', 'text/plain'), 'words.jpg.txt')
        self.assertEqual(capture.output, [
            "WARNING:odoo.tools.mimetypes:File 'image.txt' has an invalid "
                "extension for mimetype 'image/jpeg', adding '.jpg'",
            "WARNING:odoo.tools.mimetypes:File 'words.jpg' has an invalid "
                "extension for mimetype 'text/plain', adding '.txt'",
        ])
