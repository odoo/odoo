import base64

try:
    import magic
except ImportError:
    magic = None

from odoo.tests.common import BaseCase
from odoo.tools.mimetypes import fix_filename_extension, get_extension, guess_mimetype

PNG = b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVQI12P4//8/AAX+Av7czFnnAAAAAElFTkSuQmCC'
GIF = b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs="
BMP = b"""Qk1+AAAAAAAAAHoAAABsAAAAAQAAAAEAAAABABgAAAAAAAQAAAATCwAAEwsAAAAAAAAAAAAAQkdScwAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIAAAAAAAAAAAAAAAAAAAD///8A"""
JPG = """/9j/4AAQSkZJRgABAQEASABIAAD//gATQ3JlYXRlZCB3aXRoIEdJTVD/2wBDAP
//////////////////////////////////////////////////////////////////////////////////////2wBDAf///////
///////////////////////////////////////////////////////////////////////////////wgARCAABAAEDAREAAhEB
AxEB/8QAFAABAAAAAAAAAAAAAAAAAAAAAv/EABQBAQAAAAAAAAAAAAAAAAAAAAD/2gAMAwEAAhADEAAAAUf/xAAUEAEAAAAAAAA
AAAAAAAAAAAAA/9oACAEBAAEFAn//xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAEDAQE/AX//xAAUEQEAAAAAAAAAAAAAAAAAAA
AA/9oACAECAQE/AX//xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAY/An//xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBA
AE/IX//2gAMAwEAAgADAAAAEB//xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAEDAQE/EH//xAAUEQEAAAAAAAAAAAAAAAAAAAAA
/9oACAECAQE/EH//xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAE/EH//2Q=="""
SVG = b"""PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iaXNvLTg4NTktMSI/PjwhRE9DVFlQRSBzdmcgUFVCTElDICItLy9XM0MvL0RURCBTVkcgMjAwMDExMDIvL0VOIlxuICJodHRwOi8vd3d3LnczLm9yZy9UUi8yMDAwL0NSLVNWRy0yMDAwMTEwMi9EVEQvc3ZnLTIwMDAxMTAyLmR0ZCI+PHN2ZyB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIj48ZyB0cmFuc2Zvcm09InRyYW5zbGF0ZSg1MCw1MCkiPjxyZWN0IHg9IjAiIHk9IjAiIHdpZHRoPSIxNTAiIGhlaWdodD0iNTAiIHN0eWxlPSJmaWxsOnJlZDsiIC8+PC9nPjwvc3ZnPg=="""
NAMESPACED_SVG = b"""<svg:svg xmlns:svg="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <svg:rect x="10" y="10" width="80" height="80" fill="green" />
</svg:svg>"""

# single pixel webp image
WEBP = b"""UklGRjoAAABXRUJQVlA4IC4AAAAwAQCdASoBAAEAAUAmJaAAA3AA/u/uY//8s//2W/7LeM///5Bj
/dl/pJxGAAAA"""

# minimal zip file with an empty `t.txt` file
ZIP = b"""UEsDBBQACAAIAGFva1AAAAAAAAAAAAAAAAAFACAAdC50eHRVVA0AB5bgaF6W4GheluBoXnV4CwABBOgDAAAE6AMAAA
MAUEsHCAAAAAACAAAAAAAAAFBLAQIUAxQACAAIAGFva1AAAAAAAgAAAAAAAAAFACAAAAAAAAAAAACkgQAAAAB0LnR4dFVUDQAHlu
BoXpbgaF6W4GhedXgLAAEE6AMAAAToAwAAUEsFBgAAAAABAAEAUwAAAFUAAAAAAA=="""

XML = b"""<?xml version='1.0' encoding='utf-8'?>
<Document xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>123456Odoo S.A.893873733</MsgId>
      <CreDtTm>2018-11-21T09:47:32</CreDtTm>
      <NbOfTxs>0</NbOfTxs>
      <CtrlSum>0.0</CtrlSum>
      <InitgPty>
        <Nm>Odoo S.A.</Nm>
        <Id>
          <OrgId>
            <Othr>
              <Id>BE0477472701</Id>
              <Issr>KBO-BCE</Issr>
            </Othr>
          </OrgId>
        </Id>
      </InitgPty>
    </GrpHdr>
  </CstmrCdtTrfInitn>
</Document>
"""

TXT = b"""\
Hello world!
"""

class test_guess_mimetype(BaseCase):

    def test_default_mimetype_empty(self):
        mimetype = guess_mimetype(b'')
        # odoo implementation returns application/octet-stream by default
        # if available, python-magic returns application/x-empty
        self.assertIn(mimetype, ('application/octet-stream', 'application/x-empty'))

    def test_default_mimetype(self):
        mimetype = guess_mimetype(b'', default='test')
        # if available, python-magic returns application/x-empty
        self.assertIn(mimetype, ('test', 'application/x-empty'))

    def test_mimetype_octet_stream(self):
        mimetype = guess_mimetype(b'\0')
        self.assertEqual(mimetype, 'application/octet-stream')

    def test_mimetype_png(self):
        content = base64.b64decode(PNG)
        mimetype = guess_mimetype(content, default='test')
        self.assertEqual(mimetype, 'image/png')

    def test_mimetype_bmp(self):
        content = base64.b64decode(BMP)
        mimetype = guess_mimetype(content, default='test')
        # mimetype should match image/bmp, image/x-ms-bmp, ...
        self.assertRegex(mimetype, r'image/.*\bbmp')

    def test_mimetype_jpg(self):
        content = base64.b64decode(JPG)
        mimetype = guess_mimetype(content, default='test')
        self.assertEqual(mimetype, 'image/jpeg')

    def test_mimetype_gif(self):
        content = base64.b64decode(GIF)
        mimetype = guess_mimetype(content, default='test')
        self.assertEqual(mimetype, 'image/gif')

    def test_mimetype_svg(self):
        content = base64.b64decode(SVG)
        mimetype = guess_mimetype(content, default='test')
        self.assertTrue(mimetype.startswith('image/svg'))

        mimetype = guess_mimetype(NAMESPACED_SVG, default='test')
        self.assertTrue(mimetype.startswith('image/svg'))
        # Tests that whitespace padded SVG are not detected as SVG in odoo implementation
        if not magic:
            mimetype = guess_mimetype(b"   " + content, default='test')
            self.assertNotIn("svg", mimetype)


    def test_mimetype_webp(self):
        content = base64.b64decode(WEBP)
        mimetype = guess_mimetype(content, default='test')
        self.assertEqual(mimetype, 'image/webp')

    def test_mimetype_zip(self):
        content = base64.b64decode(ZIP)
        mimetype = guess_mimetype(content, default='test')
        self.assertEqual(mimetype, 'application/zip')

    def test_mimetype_xml(self):
        mimetype = guess_mimetype(XML, default='test')
        self.assertIn(mimetype, ('application/xml', 'text/xml'))

    def test_mimetype_txt(self):
        mimetype = guess_mimetype(TXT, default='test')
        self.assertEqual(mimetype, 'text/plain')

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
        with self.assertLogs('odoo.tools.mimetypes', 'WARNING') as capture:
            self.assertEqual(fix('image.txt', 'image/jpeg'), 'image.txt.jpg')
            self.assertEqual(fix('words.jpg', 'text/plain'), 'words.jpg.txt')
        self.assertEqual(capture.output, [
            "WARNING:odoo.tools.mimetypes:File 'image.txt' has an invalid "
                "extension for mimetype 'image/jpeg', adding '.jpg'",
            "WARNING:odoo.tools.mimetypes:File 'words.jpg' has an invalid "
                "extension for mimetype 'text/plain', adding '.txt'",
        ])
