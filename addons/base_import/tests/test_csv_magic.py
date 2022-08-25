# -*- coding: utf-8 -*-
"""
Tests for various autodetection magics for CSV imports
"""
import codecs

from odoo.tests import common


class ImportCase(common.TransactionCase):
    def _make_import(self, contents):
        return self.env['base_import.import'].create({
            'res_model': 'base_import.tests.models.complex',
            'file_name': 'f',
            'file_type': 'text/csv',
            'file': contents,
        })


class TestEncoding(ImportCase):
    """
    create + parse_preview -> check result options
    """

    def _check_text(self, text, encodings, **options):
        options.setdefault('quoting', '"')
        options.setdefault('separator', '\t')
        test_text = "text\tnumber\tdate\tdatetime\n%s\t1.23.45,67\t\t\n" % text
        for encoding in ['utf-8', 'utf-16', 'utf-32', *encodings]:
            if isinstance(encoding, tuple):
                encoding, es = encoding
            else:
                es = [encoding]
            preview = self._make_import(
                test_text.encode(encoding)).parse_preview(dict(options))

            self.assertIsNone(preview.get('error'))
            guessed = preview['options']['encoding']
            self.assertIsNotNone(guessed)
            self.assertIn(
                codecs.lookup(guessed).name, [
                    codecs.lookup(e).name
                    for e in es
                ]
            )

    def test_autodetect_encoding(self):
        """ Check that import preview can detect & return encoding
        """
        self._check_text("Iñtërnâtiônàlizætiøn", [('iso-8859-1', ['iso-8859-1', 'iso-8859-2'])])

        self._check_text("やぶら小路の藪柑子。海砂利水魚の、食う寝る処に住む処、パイポパイポ パイポのシューリンガン。", ['eucjp', 'shift_jis', 'iso2022_jp'])

        self._check_text("대통령은 제4항과 제5항의 규정에 의하여 확정된 법률을 지체없이 공포하여야 한다, 탄핵의 결정.", ['euc_kr', 'iso2022_kr'])

    # + control in widget
    def test_override_detection(self):
        """ ensure an explicitly specified encoding is not overridden by the
        auto-detection
        """
        s = "Iñtërnâtiônàlizætiøn".encode('utf-8')
        r = self._make_import(s + b'\ntext')\
            .parse_preview({
            'quoting': '"',
            'separator': '\t',
            'encoding': 'iso-8859-1',
        })
        self.assertIsNone(r.get('error'))
        self.assertEqual(r['options']['encoding'], 'iso-8859-1')
        self.assertEqual(r['preview'], [[s.decode('iso-8859-1'), 'text']])


class TestFileSeparator(ImportCase):

    def setUp(self):
        super().setUp()
        self.imp = self._make_import(
"""c|f
a|1
b|2
c|3
d|4
""")

    def test_explicit_success(self):
        r = self.imp.parse_preview({
            'separator': '|',
            'has_headers': True,
            'quoting': '"',
        })
        self.assertIsNone(r.get('error'))
        self.assertEqual(r['headers'], ['c', 'f'])
        self.assertEqual(r['preview'], [['a', 'b', 'c', 'd'], ['1', '2', '3', '4']])
        self.assertEqual(r['options']['separator'], '|')

    def test_explicit_fail(self):
        """ Don't protect user against making mistakes
        """
        r = self.imp.parse_preview({
            'separator': ',',
            'has_headers': True,
            'quoting': '"',
        })
        self.assertIsNone(r.get('error'))
        self.assertEqual(r['headers'], ['c|f'])
        self.assertEqual(r['preview'], [['a|1', 'b|2', 'c|3', 'd|4']])
        self.assertEqual(r['options']['separator'], ',')

    def test_guess_ok(self):
        r = self.imp.parse_preview({
            'separator': '',
            'has_headers': True,
            'quoting': '"',
        })
        self.assertIsNone(r.get('error'))
        self.assertEqual(r['headers'], ['c', 'f'])
        self.assertEqual(r['preview'], [['a', 'b', 'c', 'd'], ['1', '2', '3', '4']])
        self.assertEqual(r['options']['separator'], '|')

    def test_noguess(self):
        """ If the guesser has no idea what the separator is, it defaults to
        "," but should not set that value
        """
        imp = self._make_import('c\na\nb\nc\nd')
        r = imp.parse_preview({
            'separator': '',
            'has_headers': True,
            'quoting': '"',
        })
        self.assertIsNone(r.get('error'))
        self.assertEqual(r['headers'], ['c'])
        self.assertEqual(r['preview'], [['a', 'b', 'c', 'd']])
        self.assertEqual(r['options']['separator'], '')


class TestNumberSeparators(common.TransactionCase):
    def test_parse_float(self):
        w = self.env['base_import.import'].create({
            'res_model': 'base_import.tests.models.float',
        })
        data = w._parse_import_data(
            [
                ['1.62'], ['-1.62'], ['+1.62'], ['  +1.62  '], ['(1.62)'],
                ["1'234'567,89"], ["1.234.567'89"]
            ],
            ['value'], {}
        )
        self.assertEqual(
            [d[0] for d in data],
            ['1.62', '-1.62', '+1.62', '+1.62', '-1.62',
             '1234567.89', '1234567.89']
        )
