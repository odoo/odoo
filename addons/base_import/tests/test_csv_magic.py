# -*- coding: utf-8 -*-
"""
Tests for various autodetection magics for CSV imports
"""
import codecs

from odoo.tests import common

class TestEncoding(common.TransactionCase):
    """
    create + parse_preview -> check result options
    """

    def _check_text(self, text, encodings, **options):
        options.setdefault('quoting', '"')
        options.setdefault('separator', '\t')
        test_text = "text\tnumber\tdate\tdatetime\n%s\t1.23.45,67\t\t\n" % text
        for encoding in ['utf-8', 'utf-16', 'utf-32', *encodings]:
            preview = self._make_import(
                test_text.encode(encoding)).parse_preview(dict(options))

            guessed = preview['options']['encoding']
            self.assertIsNotNone(guessed, encoding)
            self.assertEqual(codecs.lookup(guessed).name, codecs.lookup(encoding).name)

    def test_autodetect_encoding(self):
        """ Check that import preview can detect & return encoding
        """
        self._check_text("Iñtërnâtiônàlizætiøn", ['iso-8859-1'])

        self._check_text("やぶら小路の藪柑子。海砂利水魚の、食う寝る処に住む処、パイポパイポ パイポのシューリンガン。", ['eucjp', 'shift_jis', 'iso2022_jp'])

        self._check_text("대통령은 제4항과 제5항의 규정에 의하여 확정된 법률을 지체없이 공포하여야 한다, 탄핵의 결정.", ['euc_kr', 'iso2022_kr'])

    # + control in widget
    def test_override_detection(self):
        """ ensure an explicitly specified encoding is not overridden by the
        auto-detection
        """
        s = "Iñtërnâtiônàlizætiøn".encode('utf-8')
        r = self._make_import(b'text\n' + s)\
            .parse_preview({
            'quoting': '"',
            'separator': '\t',
            'encoding': 'iso-8859-1',
        })
        self.assertEqual(r['options']['encoding'], 'iso-8859-1')
        self.assertEqual(r['preview'], [['text'], [s.decode('iso-8859-1')]])

    def _make_import(self, contents):
        return self.env['base_import.import'].create({
            'res_model': 'base_import.tests.models.complex',
            'file_name': 'f',
            'file_type': 'text/csv',
            'file': contents,
        })

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
