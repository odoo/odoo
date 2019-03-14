import base64
import unittest

from odoo.tests.common import tagged
from odoo.tools.mimetypes import guess_mimetype

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
SVG = b"""PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iaXNvLTg4NTktMSI/Pgo8IURPQ1RZUEUgc3ZnIFBVQkxJQyAiL
S8vVzNDLy9EVEQgU1ZHIDIwMDAxMTAyLy9FTiIKICJodHRwOi8vd3d3LnczLm9yZy9UUi8yMDAwL0NSLVNWRy0yMDAwMTEwMi9E
VEQvc3ZnLTIwMDAxMTAyLmR0ZCI+Cgo8c3ZnIHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiPgogIDxnIHRyYW5zZm9ybT0idHJ
hbnNsYXRlKDUwLDUwKSI+CiAgICA8cmVjdCB4PSIwIiB5PSIwIiB3aWR0aD0iMTUwIiBoZWlnaHQ9IjUwIiBzdHlsZT0iZmlsbD
pyZWQ7IiAvPgogIDwvZz4KCjwvc3ZnPgo="""
# Sample XML file: an empty SEPA Direct Debit file
XML = b"""PD94bWwgdmVyc2lvbj0nMS4wJyBlbmNvZGluZz0ndXRmLTgnPz4KPERvY3VtZW50IHhtbG5zOnhzaT0iaHR0cDovL
3d3dy53My5vcmcvMjAwMS9YTUxTY2hlbWEtaW5zdGFuY2UiIHhtbG5zPSJ1cm46aXNvOnN0ZDppc286MjAwMjI6dGVjaDp4c2Q6
cGFpbi4wMDEuMDAxLjAzIj4KICA8Q3N0bXJDZHRUcmZJbml0bj4KICAgIDxHcnBIZHI+CiAgICAgIDxNc2dJZD4xMjM0NTZPZG9
vIFMuQS44OTM4NzM3MzM8L01zZ0lkPgogICAgICA8Q3JlRHRUbT4yMDE4LTExLTIxVDA5OjQ3OjMyPC9DcmVEdFRtPgogICAgIC
A8TmJPZlR4cz4wPC9OYk9mVHhzPgogICAgICA8Q3RybFN1bT4wLjA8L0N0cmxTdW0+CiAgICAgIDxJbml0Z1B0eT4KICAgICAgI
CA8Tm0+T2RvbyBTLkEuPC9ObT4KICAgICAgICA8SWQ+CiAgICAgICAgICA8T3JnSWQ+CiAgICAgICAgICAgIDxPdGhyPgogICAg
ICAgICAgICAgIDxJZD5CRTA0Nzc0NzI3MDE8L0lkPgogICAgICAgICAgICAgIDxJc3NyPktCTy1CQ0U8L0lzc3I+CiAgICAgICA
gICAgIDwvT3Rocj4KICAgICAgICAgIDwvT3JnSWQ+CiAgICAgICAgPC9JZD4KICAgICAgPC9Jbml0Z1B0eT4KICAgIDwvR3JwSG
RyPgogIDwvQ3N0bXJDZHRUcmZJbml0bj4KPC9Eb2N1bWVudD4K"""


@tagged('standard', 'at_install')
class test_guess_mimetype(unittest.TestCase):

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
        self.assertRegexpMatches(mimetype, r'image/.*\bbmp')

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
        # Tests that whitespace padded SVG are not detected as SVG
        mimetype = guess_mimetype(b"   " + content, default='test')
        self.assertNotIn("svg", mimetype)

    def test_mimetype_xml(self):
        content = base64.b64decode(XML)
        mimetype = guess_mimetype(content, default='test')
        self.assertTrue(mimetype.startswith('application/xml'))


if __name__ == '__main__':
    unittest.main()
