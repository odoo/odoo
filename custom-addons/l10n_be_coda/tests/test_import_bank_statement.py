# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2012 Noviat nv/sa (www.noviat.be). All rights reserved.
import base64

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import file_open


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCodaFile(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='be_comp'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.bank_journal = cls.company_data['default_journal_bank']

        coda_file_path = 'l10n_be_coda/test_coda_file/Ontvangen_CODA.2013-01-11-18.59.15.txt'
        with file_open(coda_file_path, 'rb') as coda_file:
            cls.coda_file = coda_file.read()

    def test_coda_file_import(self):
        self.company_data['default_journal_bank'].create_document_from_attachment(self.env['ir.attachment'].create({
            'mimetype': 'application/text',
            'name': 'Ontvangen_CODA.2013-01-11-18.59.15.txt',
            'raw': self.coda_file,
        }).ids)

        imported_statement = self.env['account.bank.statement'].search([('company_id', '=', self.env.company.id)])
        self.assertRecordValues(imported_statement, [{
            'balance_start': 11812.70,
            'balance_end_real': 13646.05,
        }])

    def test_coda_file_import_twice(self):
        self.company_data['default_journal_bank'].create_document_from_attachment(self.env['ir.attachment'].create({
            'mimetype': 'application/text',
            'name': 'Ontvangen_CODA.2013-01-11-18.59.15.txt',
            'raw': self.coda_file,
        }).ids)

        with self.assertRaises(Exception):
            self.company_data['default_journal_bank'].create_document_from_attachment(self.env['ir.attachment'].create({
                'mimetype': 'application/text',
                'name': 'Ontvangen_CODA.2013-01-11-18.59.15.txt',
                'raw': self.coda_file,
            }).ids)

    def test_coda_special_chars(self):
        coda_special_chars = """0000001022372505        0123456789JOHN DOE                  KREDBEBB   00477472701 00000                                       2
12001BE68539007547034                  EUR0000000000100000310123DEMO COMPANY              KBC Business Account               027
2100010000ABCDEFG123456789000010000000000025500010223001500000Théâtre d'Hélène à Dümùß                             01022302701 0
2200010000                                                                                        GEBABEBB                   1 0
2300010000BE55173363943144                     ODOO SA                                                                       0 0
8027BE68539007547034                  EUR0000000000125500010223                                                                0
9               000005000000000000000000000000025500                                                                           2"""

        encodings = ('utf_8', 'cp850', 'cp858', 'cp1140', 'cp1252', 'iso8859_15', 'utf_32', 'utf_16', 'windows-1252')

        for enc in encodings:
            dummy, dummy, statements = \
                self.company_data['default_journal_bank']._parse_bank_statement_file(self.env['ir.attachment'].create({
                    'mimetype': 'application/text',
                    'name': 'CODA-Test',
                    'raw': coda_special_chars.encode(enc),
                }))
            self.assertEqual(statements[0]['transactions'][0]['payment_ref'][:24], "Théâtre d'Hélène à Dümùß")
