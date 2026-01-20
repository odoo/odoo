import typing
import unittest

from odoo.tests import tagged, BaseCase
from odoo.tools import file_path
from odoo.tools.mimetypes import _odoo_guess_mimetype, _odoo_guess_file_mimetype, fix_filename_extension, get_extension, guess_mimetype, guess_file_mimetype
from pathlib import Path

TEST_FOLDER = Path(file_path('base/tests/files'))


class MimeGuessingCases:
    allow_inherited_tests_method: bool = True
    guess_mimetype: typing.Callable[[bytes, str], str]
    guess_file_mimetype: typing.Callable[[str, str], str]

    def test_doc(self):
        self.assertEqual(
            self.guess_file_mimetype(TEST_FOLDER / 'file.doc'),
            'application/msword',
        )

    def test_xls(self):
        self.assertEqual(
            self.guess_file_mimetype(TEST_FOLDER / 'file.xls'),
            'application/vnd.ms-excel',
        )

    def test_docx(self):
        self.assertEqual(
            self.guess_file_mimetype(TEST_FOLDER / 'file.docx'),
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )

    def test_xlsx(self):
        self.assertEqual(
            self.guess_file_mimetype(TEST_FOLDER / 'file.xlsx'),
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def test_xlsx_2025(self):
        self.assertEqual(
            self.guess_file_mimetype(TEST_FOLDER / 'file.2025.xlsx'),
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def test_odt(self):
        self.assertEqual(
            self.guess_file_mimetype(TEST_FOLDER / 'file.odt'),
            'application/vnd.oasis.opendocument.text',
        )

    def test_ods(self):
        self.assertEqual(
            self.guess_file_mimetype(TEST_FOLDER / 'file.ods'),
            'application/vnd.oasis.opendocument.spreadsheet',
        )

    def test_zip(self):
        self.assertEqual(
            self.guess_file_mimetype(TEST_FOLDER / 'file.zip'),
            'application/zip',
        )

    def test_gif(self):
        self.assertEqual(
            self.guess_file_mimetype(TEST_FOLDER / 'file.gif'),
            'image/gif',
        )

    def test_jpeg(self):
        self.assertEqual(
            self.guess_file_mimetype(TEST_FOLDER / 'file.jpg'),
            'image/jpeg',
        )

    def test_text(self):
        self.assertEqual(
            self.guess_mimetype(b'abc\n\t\r'),
            'text/plain',
        )

    def test_ppt(self):
        self.assertEqual(
            self.guess_file_mimetype(TEST_FOLDER / 'file.ppt'),
            'application/vnd.ms-powerpoint',
        )

    def test_pptx(self):
        self.assertEqual(
            self.guess_file_mimetype(TEST_FOLDER / 'file.pptx'),
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        )

    def test_pdf(self):
        self.assertEqual(
            self.guess_file_mimetype(TEST_FOLDER / 'file.pdf'),
            'application/pdf',
        )

    def test_ico(self):
        self.assertEqual(
            self.guess_file_mimetype(TEST_FOLDER / 'file.ico'),
            'image/vnd.microsoft.icon',
        )

    def test_webp(self):
        self.assertEqual(
            self.guess_file_mimetype(TEST_FOLDER / 'file.webp'),
            'image/webp',
        )

    def test_xml(self):
        self.assertEqual(
            self.guess_file_mimetype(TEST_FOLDER / 'file.xml'),
            'text/xml',
        )

    def test_png(self):
        self.assertEqual(
            self.guess_file_mimetype(TEST_FOLDER / 'file.png'),
            'image/png',
        )

    def test_bmp(self):
        self.assertEqual(
            self.guess_file_mimetype(TEST_FOLDER / 'file.bmp'),
            'image/bmp',
        )

    def test_svg(self):
        self.assertEqual(
            self.guess_mimetype(b'<svg></svg>'),
            'image/svg+xml',
        )

    def test_namespaced_svg(self):
        self.assertEqual(
            self.guess_mimetype(b'<svg:svg></svg:svg>'),
            'image/svg+xml',
        )

    def test_empty(self):
        self.assertEqual(
            self.guess_mimetype(b''),
            'application/x-empty',
        )

    def test_octet_stream(self):
        self.assertEqual(
            self.guess_mimetype(b'\0'),
            'application/octet-stream',
        )


@tagged('at_install', '-post_install')
class TestMimeGuessingOdoo(BaseCase, MimeGuessingCases):
    guess_mimetype = staticmethod(_odoo_guess_mimetype)
    guess_file_mimetype = staticmethod(_odoo_guess_file_mimetype)

    def test_csv(self):
        self.assertEqual(
            self.guess_file_mimetype(TEST_FOLDER / 'file.csv'),
            'text/plain',
        )

    def test_default_param(self):
        self.assertEqual(
            self.guess_mimetype(b'\1', default='test'),
            'test',
        )

    def test_get_extension(self):
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

    def test_fix_filename_extension(self):
        fix = fix_filename_extension

        # Valid
        self.assertEqual(fix('words.txt', 'text/plain'), 'words.txt')
        self.assertEqual(fix('image.jpg', 'image/jpeg'), 'image.jpg')
        self.assertEqual(fix('image.jpeg', 'image/jpeg'), 'image.jpeg')
        self.assertEqual(fix('sheet.xls', 'application/vnd.ms-excel'), 'sheet.xls')
        self.assertEqual(fix('sheet.xls', 'application/CDFV2'), 'sheet.xls')
        self.assertEqual(fix('sheet.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'), 'sheet.xlsx')
        self.assertEqual(fix('sheet.xlsx', 'application/zip'), 'sheet.xlsx')

        # Invalid
        with self.assertLogs('odoo.tools.mimetypes', 'WARNING') as capture:
            self.assertEqual(fix('image.txt', 'image/jpeg'), 'image.txt.jpg')
            self.assertEqual(fix('words.jpg', 'text/plain'), 'words.jpg.txt')

        self.assertEqual(capture.output, [
            "WARNING:odoo.tools.mimetypes:File 'image.txt' has an invalid extension for mimetype 'image/jpeg', adding '.jpg'",
            "WARNING:odoo.tools.mimetypes:File 'words.jpg' has an invalid extension for mimetype 'text/plain', adding '.txt'",
        ])


@unittest.skipIf(guess_mimetype is _odoo_guess_mimetype, "python-magic not installed")
@tagged('at_install', '-post_install')
class TestMimeGuessingMagic(BaseCase, MimeGuessingCases):
    guess_mimetype = staticmethod(guess_mimetype)
    guess_file_mimetype = staticmethod(guess_file_mimetype)

    def test_csv(self):
        self.assertEqual(
            self.guess_file_mimetype(TEST_FOLDER / 'file.csv'),
            'text/csv',
        )

    def test_default_param(self):
        self.assertEqual(
            self.guess_mimetype(b'', default='test'),
            'application/x-empty',
        )
