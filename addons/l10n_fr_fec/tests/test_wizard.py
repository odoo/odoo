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
    def setUpClass(cls, chart_template_ref='l10n_fr.l10n_fr_pcg_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        company = cls.company_data['company']
        company.vat = 'FR13542107651'

        lines_data = [(1437.12, 'Hello\tDarkness'), (1676.64, 'my\rold\nfriend'), (3353.28, '\t\t\r')]

        with freeze_time('2021-05-02'):
            today = fields.Date.today().strftime('%Y-%m-%d')

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
            'date': today,
            'invoice_date': today,
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

    def test_generate_fec_sanitize_pieceref(self):
        self.wizard.generate_fec()
        expected_content = (
            "JournalCode|JournalLib|EcritureNum|EcritureDate|CompteNum|CompteLib|CompAuxNum|CompAuxLib|PieceRef|PieceDate|EcritureLib|Debit|Credit|EcritureLet|DateLet|ValidDate|Montantdevise|Idevise\r\n"
            "INV|Customer Invoices|INV/2021/00001|20210502|701100|Ventes de produits finis (ou groupe) A|||-|20210502|Hello Darkness|0,00| 000000000001437,12|||20210502|-000000000001437,12|EUR\r\n"
            "INV|Customer Invoices|INV/2021/00001|20210502|701100|Ventes de produits finis (ou groupe) A|||-|20210502|my old friend|0,00| 000000000001676,64|||20210502|-000000000001676,64|EUR\r\n"
            "INV|Customer Invoices|INV/2021/00001|20210502|701100|Ventes de produits finis (ou groupe) A|||-|20210502|/|0,00| 000000000003353,28|||20210502|-000000000003353,28|EUR\r\n"
            "INV|Customer Invoices|INV/2021/00001|20210502|445710|TVA collectée|||-|20210502|TVA 20,0%|0,00| 000000000001293,41|||20210502|-000000000001293,41|EUR\r\n"
            f"INV|Customer Invoices|INV/2021/00001|20210502|411100|Clients - Ventes de biens ou de prestations de services|{self.partner_a.id}|partner_a|-|20210502|INV/2021/00001| 000000000007760,45|0,00|||20210502| 000000000007760,45|EUR"
        )
        content = base64.b64decode(self.wizard.fec_data).decode()
        self.assertEqual(expected_content, content)
