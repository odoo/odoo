# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import timedelta

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import fields


@tagged('post_install', '-at_install')
class TestAccountFrFec(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        company = cls.company_data['company']
        cls.env.user.company_id = company
        company.vat = 'FR13542107651'

        lines_data = [(1437.12, 'Hello\tDarkness'), (1676.64, 'my\rold\nfriend'), (3353.28, '\t\t\r')]
        today = fields.Date.today().strftime('%Y-%m-%d')
        cls.invoice_a = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'date': today,
            'invoice_date': today,
            'currency_id': cls.company_data['company'].currency_id.id,
            'invoice_line_ids': [(0, None, {
                'name': name,
                'product_id': cls.product_a.id,
                'quantity': 1,
                'tax_ids': [(6, 0, [cls.tax_sale_a.id])],
                'price_unit': price_unit,
            }) for price_unit, name in lines_data]
        })
        cls.invoice_a.action_post()

        cls.wizard = cls.env['account.fr.fec'].create({
            'date_from': fields.Date.today() - timedelta(days=1),
            'date_to': fields.Date.today(),
            'export_type': 'official',
            'test_file': True,
        })

    def test_generate_fec_sanitize_pieceref(self):
        self.wizard.generate_fec()
        today = fields.Date.today().strftime('%Y%m%d')
        expected_content = (
            "JournalCode|JournalLib|EcritureNum|EcritureDate|CompteNum|CompteLib|CompAuxNum|CompAuxLib|PieceRef|PieceDate|EcritureLib|Debit|Credit|EcritureLet|DateLet|ValidDate|Montantdevise|Idevise\r\n"
            f"INV|Customer Invoices|INV/2021/11/0001|{today}|400000|Product Sales|||-|{today}|Hello Darkness|0,00| 000000000001437,12|||{today}|-000000000001437,12|USD\r\n"
            f"INV|Customer Invoices|INV/2021/11/0001|{today}|400000|Product Sales|||-|{today}|my old friend|0,00| 000000000001676,64|||{today}|-000000000001676,64|USD\r\n"
            f"INV|Customer Invoices|INV/2021/11/0001|{today}|400000|Product Sales|||-|{today}|/|0,00| 000000000003353,28|||{today}|-000000000003353,28|USD\r\n"
            f"INV|Customer Invoices|INV/2021/11/0001|{today}|251000|Tax Received|||-|{today}|Tax 15.00%|0,00| 000000000000970,06|||{today}|-000000000000970,06|USD\r\n"
            f"INV|Customer Invoices|INV/2021/11/0001|{today}|121000|Account Receivable|{self.partner_a.id}|partner_a|-|{today}|INV/2021/11/0001| 000000000007437,10|0,00|||{today}| 000000000007437,10|USD"
        )
        content = base64.b64decode(self.wizard.fec_data).decode()
        self.assertEqual(expected_content, content)
