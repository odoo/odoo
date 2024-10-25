# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import timedelta
from freezegun import freeze_time

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import fields, Command


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountFrFec(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='fr'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        company = cls.company_data['company']
        company.vat = 'FR13542107651'

        lines_data = [(1437.12, 'Hello\tDarkness'), (1676.64, 'my\rold\nfriend'), (3353.28, '\t\t\r')]

        with freeze_time('2021-05-02'):
            cls.today = fields.Date.today().strftime('%Y-%m-%d')

            cls.wizard = cls.env['account.fr.fec'].create({
                'date_from': fields.Date.today() - timedelta(days=1),
                'date_to': fields.Date.today(),
                'export_type': 'official',
                'test_file': True,
            })

        cls.tax_sale_a = cls.env['account.tax'].create({
            'name': "TVA 20,0%",
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'amount': 20,
            'invoice_repartition_line_ids': [
                Command.create({
                    'factor_percent': 100.0,
                    'repartition_type': 'base',
                }),
                Command.create({
                    'repartition_type': 'tax',
                    'factor_percent': 100.0,
                    'account_id': cls.env['account.account'].search([('code', '=', "445710")], limit=1).id,
                })
            ]
        })

        cls.invoice_a = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'date': cls.today,
            'invoice_date': cls.today,
            'currency_id': company.currency_id.id,
            'invoice_line_ids': [(0, None, {
                'name': name,
                'product_id': cls.product_a.id,
                'quantity': 1,
                'tax_ids': [(6, 0, [cls.tax_sale_a.id])],
                'price_unit': price_unit,
            }) for price_unit, name in lines_data]
        })
        cls.invoice_a.action_post()

        cls.expected_report = (
            "JournalCode|JournalLib|EcritureNum|EcritureDate|CompteNum|CompteLib|CompAuxNum|CompAuxLib|PieceRef|PieceDate|EcritureLib|Debit|Credit|EcritureLet|DateLet|ValidDate|Montantdevise|Idevise\r\n"
            "INV|Customer Invoices|INV/2021/00001|20210502|701100|Finished products (or group) A|||-|20210502|Hello Darkness|0,00| 000000000001437,12|||20210502|-000000000001437,12|EUR\r\n"
            "INV|Customer Invoices|INV/2021/00001|20210502|701100|Finished products (or group) A|||-|20210502|my old friend|0,00| 000000000001676,64|||20210502|-000000000001676,64|EUR\r\n"
            "INV|Customer Invoices|INV/2021/00001|20210502|701100|Finished products (or group) A|||-|20210502|/|0,00| 000000000003353,28|||20210502|-000000000003353,28|EUR\r\n"
            "INV|Customer Invoices|INV/2021/00001|20210502|445710|VAT collected|||-|20210502|TVA 20,0%|0,00| 000000000001293,41|||20210502|-000000000001293,41|EUR\r\n"
            f"INV|Customer Invoices|INV/2021/00001|20210502|411100|Customers - Sales of goods or services|{cls.partner_a.id}|partner_a|-|20210502|INV/2021/00001| 000000000007760,45|0,00|||20210502| 000000000007760,45|EUR"
        )

    def test_generate_fec_sanitize_pieceref(self):
        self.wizard.generate_fec()
        content = base64.b64decode(self.wizard.fec_data).decode()
        self.assertEqual(self.expected_report, content)

    def test_generate_fec_exclude_journals(self):
        journal = self.company_data['default_journal_misc']
        self.env['account.move'].create({
            'journal_id': journal.id,
            'date': self.today,
            'line_ids': [
                Command.create({
                    'account_id': self.company_data['default_account_payable'].id,
                    'debit': 500,
                    'company_id': self.company_data['company'].id
                }),
                Command.create({
                    'account_id': self.company_data['default_account_receivable'].id,
                    'credit': 500,
                    'company_id': self.company_data['company'].id
                })
            ]
        }).action_post()
        self.env.flush_all()

        self.wizard.generate_fec()
        expected_content = self.expected_report + (
            "\r\n"
            "MISC|Miscellaneous Operations|MISC/2021/05/0001|20210502|400000|Suppliers and related accounts|||-|20210502|/| 000000000000500,00|0,00|||20210502| 000000000000500,00|EUR\r\n"
            "MISC|Miscellaneous Operations|MISC/2021/05/0001|20210502|411100|Customers - Sales of goods or services|||-|20210502|/|0,00| 000000000000500,00|||20210502|-000000000000500,00|EUR"
        )
        content = base64.b64decode(self.wizard.fec_data).decode()
        self.assertEqual(expected_content, content)

        self.wizard.excluded_journal_ids = journal
        self.wizard.generate_fec()
        content = base64.b64decode(self.wizard.fec_data).decode()
        self.assertEqual(self.expected_report, content)

    def test_fec_sub_companies(self):
        """When exporting FEC, data from child companies should be included"""
        main_company = self.env.company
        branch_a, branch_b = self.env['res.company'].create([
            {
                'name': 'Branch A',
                'country_id': main_company.country_id.id,
                'parent_id': main_company.id,
            }, {
                'name': 'Branch B',
                'country_id': main_company.country_id.id,
                'parent_id': main_company.id
            }
        ])
        branch_a1 = self.env['res.company'].create({
            'name': 'Branch A1',
            'country_id': main_company.country_id.id,
            'parent_id': branch_a.id,
        })

        self.cr.precommit.run()  # load the COA
        all_companies = (main_company + branch_a + branch_a1 + branch_b)

        for i, company in enumerate(all_companies, start=1):
            self.init_invoice('out_invoice', invoice_date=self.today, post=True, amounts=[i * 100], company=company)

        self.env.flush_all()

        expected_content = self.expected_report + (
            "\r\n"
            "INV|Customer Invoices|INV/2021/00002|20210502|707100|Goods for resale (or group) A|||-|20210502|test line|0,00| 000000000000100,00|||20210502|-000000000000100,00|EUR\r\n"
            f"INV|Customer Invoices|INV/2021/00002|20210502|411100|Customers - Sales of goods or services|{self.partner_a.id}|partner_a|-|20210502|INV/2021/00002| 000000000000100,00|0,00|||20210502| 000000000000100,00|EUR\r\n"
            "INV|Customer Invoices|INV/2021/00003|20210502|707100|Goods for resale (or group) A|||-|20210502|test line|0,00| 000000000000200,00|||20210502|-000000000000200,00|EUR\r\n"
            f"INV|Customer Invoices|INV/2021/00003|20210502|411100|Customers - Sales of goods or services|{self.partner_a.id}|partner_a|-|20210502|INV/2021/00003| 000000000000200,00|0,00|||20210502| 000000000000200,00|EUR\r\n"
            "INV|Customer Invoices|INV/2021/00004|20210502|707100|Goods for resale (or group) A|||-|20210502|test line|0,00| 000000000000300,00|||20210502|-000000000000300,00|EUR\r\n"
            f"INV|Customer Invoices|INV/2021/00004|20210502|411100|Customers - Sales of goods or services|{self.partner_a.id}|partner_a|-|20210502|INV/2021/00004| 000000000000300,00|0,00|||20210502| 000000000000300,00|EUR\r\n"
            "INV|Customer Invoices|INV/2021/00005|20210502|707100|Goods for resale (or group) A|||-|20210502|test line|0,00| 000000000000400,00|||20210502|-000000000000400,00|EUR\r\n"
            f"INV|Customer Invoices|INV/2021/00005|20210502|411100|Customers - Sales of goods or services|{self.partner_a.id}|partner_a|-|20210502|INV/2021/00005| 000000000000400,00|0,00|||20210502| 000000000000400,00|EUR"
        )

        self.wizard.generate_fec()
        content = base64.b64decode(self.wizard.fec_data).decode()
        self.assertEqual(expected_content, content)

        # Select only parent company
        self.env.user.write({
            'company_ids': [Command.set(main_company.ids)],
            'company_id': main_company.id,
        })

        expected_content = self.expected_report + (
            "\r\n"
            "INV|Customer Invoices|INV/2021/00002|20210502|707100|Goods for resale (or group) A|||-|20210502|test line|0,00| 000000000000100,00|||20210502|-000000000000100,00|EUR\r\n"
            f"INV|Customer Invoices|INV/2021/00002|20210502|411100|Customers - Sales of goods or services|{self.partner_a.id}|partner_a|-|20210502|INV/2021/00002| 000000000000100,00|0,00|||20210502| 000000000000100,00|EUR"
        )

        self.wizard.generate_fec()
        content = base64.b64decode(self.wizard.fec_data).decode()
        self.assertEqual(expected_content, content)
