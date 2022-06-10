# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import logging
from lxml import etree

from odoo.tests import tagged
from odoo.addons.l10n_it_edi_sdicoop.tests.test_edi_xml import TestItEdi

_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItEdiReverseCharge(TestItEdi):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.french_partner = cls.env['res.partner'].create({
            'name': 'Alessi',
            'vat': 'FR15437982937',
            'country_id': cls.env.ref('base.fr').id,
            'street': 'Avenue Test rue',
            'zip': '84000',
            'city': 'Avignon',
            'is_company': True
        })

        def get_tags(*tag_codes):
            return cls.env['account.account.tag'].search([('applicability', '=', 'taxes'), ('name', 'in', tag_codes)]).ids

        tax_data = {
            'name': 'Tax 4% (Goods) Reverse Charge',
            'amount': 4.0,
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'invoice_repartition_line_ids': [
                (5, 0, 0),
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'tag_ids': get_tags('+vp3'),
                }),
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    'tag_ids': get_tags('+vj9'),
                }),
                (0, 0, {
                    'factor_percent': -100,
                    'repartition_type': 'tax',
                })
            ],
            'refund_repartition_line_ids': [
                (5, 0, 0),
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'base'
                }),
                (0, 0, {
                    'factor_percent': 100,
                    'repartition_type': 'tax',
                    # 'account_id': cls.env.ref('1601'),
                }),
                (0, 0, {
                    'factor_percent': -100,
                    'repartition_type': 'tax'
                })
            ]
        }
        cls.purchase_tax_4p = cls.env['account.tax'].with_company(cls.company).create(tax_data)
        cls.line_tax_4p = cls.standard_line.copy()
        cls.line_tax_4p['tax_ids'] = [(6, 0, cls.purchase_tax_4p.ids)]

        tax_data_22p = {**tax_data, 'name': 'Tax 22% purchase Reverse Charge', 'amount': 22.0}
        cls.purchase_tax_22p = cls.env['account.tax'].with_company(cls.company).create(tax_data_22p)
        cls.line_tax_22p = cls.standard_line.copy()
        cls.line_tax_22p['tax_ids'] = [(6, 0, cls.purchase_tax_22p.ids)]

        tax_data_0v = {**tax_data, "type_tax_use": "sale", "amount": 0}
        cls.sale_tax_0v = cls.env['account.tax'].with_company(cls.company).create(tax_data_0v)
        cls.line_tax_sale = cls.standard_line.copy()
        cls.line_tax_sale['tax_ids'] = [(6, 0, cls.sale_tax_0v.ids)]

        product_a = cls.env['product.product'].with_company(cls.company).create({
            'name': 'product_a',
            'lst_price': 1000.0,
            'standard_price': 800.0,
            'type': 'consu',
            'taxes_id': [(6, 0, cls.sale_tax_0v.ids)],
            'supplier_taxes_id': [(6, 0, cls.purchase_tax_4p.ids)],
        })
        product_b = cls.env['product.product'].with_company(cls.company).create({
            'name': 'product_b',
            'lst_price': 1000.0,
            'standard_price': 800.0,
            'type': 'consu',
            'taxes_id': [(6, 0, cls.sale_tax_0v.ids)],
            'supplier_taxes_id': [(6, 0, cls.purchase_tax_4p.ids)],
        })

        cls.reverse_charge_invoice = cls.env['account.move'].with_company(cls.company).create({
            'company_id': cls.company.id,
            'move_type': 'out_invoice',
            'invoice_date': datetime.date(2022, 3, 24),
            'partner_id': cls.french_partner.id,
            'partner_bank_id': cls.test_bank.id,
            'invoice_line_ids': [
                (0, 0, {
                    **cls.line_tax_sale,
                    'name': 'Product A',
                    'product_id': product_a.id,
                }),
                (0, 0, {
                    **cls.line_tax_sale,
                    'name': 'Product B',
                    'product_id': product_b.id,
                })
            ],
        })
        cls.reverse_charge_bill = cls.env['account.move'].with_company(cls.company).create({
            'company_id': cls.company.id,
            'move_type': 'in_invoice',
            'invoice_date': datetime.date(2022, 3, 24),
            'partner_id': cls.french_partner.id,
            'partner_bank_id': cls.test_bank.id,
            'invoice_line_ids': [
                (0, 0, {
                    **cls.line_tax_22p,
                    'name': 'Product A',
                    'product_id': product_a.id,
                }),
                (0, 0, {
                    **cls.line_tax_4p,
                    'name': 'Product B, taxed 4%',
                    'product_id': product_b.id,
                })
            ],
        })
        cls.reverse_charge_invoice._post()
        cls.reverse_charge_bill._post()

    def _cleanup_etree(self, content):
        return self.with_applied_xpath(
            etree.fromstring(content),
            "<xpath expr='//Allegati' position='replace'><Allegati/></xpath>")

    def _test_invoice_with_sample_file(self, invoice, filename):
        self.assertXmlTreeEqual(
            self._cleanup_etree(self._get_test_file_content(filename)),
            self._cleanup_etree(invoice._export_as_xml()))

    def test_reverse_charge_invoice(self):
        self._test_invoice_with_sample_file(self.reverse_charge_invoice, "reverse_charge_invoice.xml")

    def test_reverse_charge_bill(self):
        self._test_invoice_with_sample_file(self.reverse_charge_bill, "reverse_charge_bill.xml")
