import os.path
import unittest

from odoo.tests import BaseCase
from odoo.tools.mimetypes import _odoo_guess_mimetype, guess_mimetype
from odoo.tools.misc import file_open
<<<<<<< 08b62a4bbcc6f9a391b2cc00a621ef4c76100229

||||||| 612ac9212eb3b5802d882325c475a2f727e8b0ca
from odoo.tools.mimetypes import guess_mimetype
=======
from odoo.tools.mimetypes import guess_mimetype, magic
>>>>>>> 9dc347b560cb315546f4920258ced808708a40cc

def contents(extension):
    with file_open(os.path.join(
        os.path.dirname(__file__),
        'testfiles',
        'case.{}'.format(extension)
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

<<<<<<< 08b62a4bbcc6f9a391b2cc00a621ef4c76100229
    def test_xls(self):
||||||| 612ac9212eb3b5802d882325c475a2f727e8b0ca
    def test_xlsx_2025(self):
        # only work when python-magic is not installed
=======
    def test_xlsx_2025(self):
        # only work when python-magic is not installed otherwise seen as a zip
>>>>>>> 9dc347b560cb315546f4920258ced808708a40cc
        self.assertEqual(
<<<<<<< 08b62a4bbcc6f9a391b2cc00a621ef4c76100229
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
||||||| 612ac9212eb3b5802d882325c475a2f727e8b0ca
            guess_mimetype(contents('2025.xlsx')),
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
=======
            guess_mimetype(contents('2025.xlsx')),
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if magic is None else 'application/zip',
>>>>>>> 9dc347b560cb315546f4920258ced808708a40cc
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

<<<<<<< 08b62a4bbcc6f9a391b2cc00a621ef4c76100229
    def test_jpeg(self):
||||||| 612ac9212eb3b5802d882325c475a2f727e8b0ca
    def test_unknown(self):
=======
    def test_unknown(self):
        expected_mimetype = 'text/plain' if magic is None else 'text/csv'
>>>>>>> 9dc347b560cb315546f4920258ced808708a40cc
        self.assertEqual(
<<<<<<< 08b62a4bbcc6f9a391b2cc00a621ef4c76100229
            self.guess_mimetype(contents('jpg')),
            'image/jpeg',
        )

    def test_text(self):
        self.assertEqual(
            self.guess_mimetype(b"Some text with no special format.\n"),
            'text/plain',
        )

    def test_unkown(self):
        self.assertEqual(
            self.guess_mimetype(b"\1\2\3\1\2\3\1\2\3\1\2\3\1\2\3"),
            'application/octet-stream',
        )


class TestMimeGuessingOdoo(BaseCase, MimeGuessingCases):
    guess_mimetype = staticmethod(_odoo_guess_mimetype)

    def test_csv(self):
        self.assertEqual(
            self.guess_mimetype(contents('csv')),
            'text/plain',
        )


@unittest.skipIf(guess_mimetype is _odoo_guess_mimetype, "python-magic not installed")
class TestMimeGuessingMagic(BaseCase, MimeGuessingCases):
    guess_mimetype = staticmethod(guess_mimetype)

    def test_csv(self):
        self.assertEqual(
            self.guess_mimetype(contents('csv')),
            'text/csv',
||||||| 612ac9212eb3b5802d882325c475a2f727e8b0ca
            guess_mimetype(contents('csv')),
            'text/plain'
=======
            guess_mimetype(contents('csv')),
            expected_mimetype
>>>>>>> 9dc347b560cb315546f4920258ced808708a40cc
        )
