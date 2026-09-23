import base64
import unittest

from odoo.libs.filesystem.mimetypes import (
    fix_filename_extension,
    get_extension,
    guess_mimetype,
)
from odoo.libs.filesystem.samples import (
    BMP,
    GIF,
    JPG,
    NAMESPACED_SVG,
    PNG,
    SVG,
    TXT,
    WEBP,
    XML,
    ZIP,
)


class test_guess_mimetype(unittest.TestCase):
    def test_default_mimetype_empty(self):
        mimetype = guess_mimetype(b"")
        self.assertIn(mimetype, ("application/octet-stream", "application/x-empty"))

    def test_default_mimetype(self):
        mimetype = guess_mimetype(b"", default="test")
        self.assertIn(mimetype, ("test", "application/x-empty"))

    def test_mimetype_octet_stream(self):
        mimetype = guess_mimetype(b"\0")
        self.assertEqual(mimetype, "application/octet-stream")

    def test_mimetype_png(self):
        content = base64.b64decode(PNG)
        mimetype = guess_mimetype(content, default="test")
        self.assertEqual(mimetype, "image/png")

    def test_mimetype_bmp(self):
        content = base64.b64decode(BMP)
        mimetype = guess_mimetype(content, default="test")
        self.assertRegex(mimetype, r"image/.*\bbmp")

    def test_mimetype_jpg(self):
        content = base64.b64decode(JPG)
        mimetype = guess_mimetype(content, default="test")
        self.assertEqual(mimetype, "image/jpeg")

    def test_mimetype_gif(self):
        content = base64.b64decode(GIF)
        mimetype = guess_mimetype(content, default="test")
        self.assertEqual(mimetype, "image/gif")

    def test_mimetype_svg(self):
        content = base64.b64decode(SVG)
        mimetype = guess_mimetype(content, default="test")
        self.assertTrue(mimetype.startswith("image/svg"))

        mimetype = guess_mimetype(NAMESPACED_SVG, default="test")
        self.assertTrue(mimetype.startswith("image/svg"))

    def test_mimetype_webp(self):
        content = base64.b64decode(WEBP)
        mimetype = guess_mimetype(content, default="test")
        self.assertEqual(mimetype, "image/webp")

    def test_mimetype_zip(self):
        content = base64.b64decode(ZIP)
        mimetype = guess_mimetype(content, default="test")
        self.assertEqual(mimetype, "application/zip")

    def test_mimetype_xml(self):
        mimetype = guess_mimetype(XML, default="test")
        self.assertIn(mimetype, ("application/xml", "text/xml"))

    def test_mimetype_txt(self):
        mimetype = guess_mimetype(TXT, default="test")
        self.assertEqual(mimetype, "text/plain")

    def test_mimetype_get_extension(self):
        self.assertEqual(get_extension("filename.Abc"), ".abc")
        self.assertEqual(get_extension("filename.scss"), ".scss")
        self.assertEqual(get_extension("filename.torrent"), ".torrent")
        self.assertEqual(get_extension("filename.ab_c"), ".ab_c")
        self.assertEqual(get_extension(".htaccess"), "")
        self.assertEqual(get_extension("filename.tar.gz"), ".gz")
        self.assertEqual(get_extension("filename"), "")
        self.assertEqual(get_extension("filename."), "")
        self.assertEqual(get_extension("filename.not_alnum"), "")
        self.assertEqual(get_extension("filename.with space"), "")
        self.assertEqual(get_extension("filename.notAnExtension"), "")

    def test_get_extension_keeps_a_long_extension_as_written(self):
        self.assertEqual(get_extension("notes.markdown"), ".markdown")
        self.assertEqual(get_extension("page.MHTML"), ".mhtml")
        self.assertEqual(get_extension("manual.texinfo"), ".texinfo")
        self.assertEqual(get_extension("clip.3gpp2"), ".3gpp2")

    def test_mimetype_fix_extension(self):
        fix = fix_filename_extension
        self.assertEqual(fix("words.txt", "text/plain"), "words.txt")
        self.assertEqual(fix("image.jpg", "image/jpeg"), "image.jpg")
        self.assertEqual(fix("image.jpeg", "image/jpeg"), "image.jpeg")
        self.assertEqual(fix("sheet.xls", "application/vnd.ms-excel"), "sheet.xls")
        self.assertEqual(fix("sheet.xls", "application/CDFV2"), "sheet.xls")
        xlsx_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        self.assertEqual(fix("sheet.xlsx", xlsx_mime), "sheet.xlsx")
        self.assertEqual(fix("sheet.xlsx", "application/zip"), "sheet.xlsx")
        with self.assertLogs("odoo.libs.filesystem.mimetypes", "WARNING") as capture:
            self.assertEqual(fix("image.txt", "image/jpeg"), "image.txt.jpg")
            self.assertEqual(fix("words.jpg", "text/plain"), "words.jpg.txt")
        self.assertEqual(
            capture.output,
            [
                (
                    "WARNING:odoo.libs.filesystem.mimetypes:File 'image.txt' has an invalid "
                    "extension for mimetype 'image/jpeg', adding '.jpg'"
                ),
                (
                    "WARNING:odoo.libs.filesystem.mimetypes:File 'words.jpg' has an invalid "
                    "extension for mimetype 'text/plain', adding '.txt'"
                ),
            ],
        )
