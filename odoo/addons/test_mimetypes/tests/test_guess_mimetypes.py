# -*- coding: utf-8 -*-
import os.path

from odoo.tests.common import BaseCase
from odoo.tools.misc import file_open
from odoo.tools.mimetypes import guess_mimetype

def contents(extension):
    with file_open(os.path.join(
        os.path.dirname(__file__),
        'testfiles',
        'case.{}'.format(extension)
    ), 'rb') as f:
        return f.read()


class TestMimeGuessing(BaseCase):
    def test_doc(self):
        self.assertEqual(
            guess_mimetype(contents('doc')),
            'application/msword'
        )
    def test_xls(self):
        self.assertEqual(
            guess_mimetype(contents('xls')),
            'application/vnd.ms-excel'
        )
    def test_docx(self):
        self.assertEqual(
            guess_mimetype(contents('docx')),
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    def test_xlsx(self):
        self.assertEqual(
            guess_mimetype(contents('xlsx')),
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    def test_odt(self):
        self.assertEqual(
            guess_mimetype(contents('odt')),
            'application/vnd.oasis.opendocument.text'
        )
    def test_ods(self):
        self.assertEqual(
            guess_mimetype(contents('ods')),
            'application/vnd.oasis.opendocument.spreadsheet'
        )

    def test_zip(self):
        self.assertEqual(
            guess_mimetype(contents('zip')),
            'application/zip'
        )

    def test_gif(self):
        self.assertEqual(
            guess_mimetype(contents('gif')),
            'image/gif'
        )
    def test_jpeg(self):
        self.assertEqual(
            guess_mimetype(contents('jpg')),
            'image/jpeg'
        )

    def test_unknown(self):
        self.assertEqual(
            guess_mimetype(contents('csv')),
            'application/octet-stream'
        )
