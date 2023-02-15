# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo import fields
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged('-at_install', 'post_install')
class TestSaleReportCurrencyRate(SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env['res.company'].create({
            'name': 'Test Company',
            'currency_id': cls.env.ref('base.USD').id,
        })

    def test_sale_report_foreign_currency(self):
        # Test the amounts shown in the sales report for orders in foreign currency
        currency_eur = self._enable_currency('EUR')

        eur_pricelist = self.env['product.pricelist'].create({
            'name': 'Pricelist (EUR)',
            'currency_id': currency_eur.id,
        })

        with freeze_time('2022-02-22'):
            self.env['res.currency.rate'].create({
                'name': fields.Date.today(),
                'company_rate': 3.0,
                'currency_id': currency_eur.id,
                'company_id': self.company.id,
            })
            eur_order = self.env['sale.order'].with_company(self.company).create({
                'partner_id': self.partner.id,
                'pricelist_id': eur_pricelist.id,
                'date_order': fields.Date.today(),
                'order_line': [
                    Command.create({
                        'product_id': self.product.id,
                        'product_uom_qty': 1.0,
                    }),
                ]
            })
            # the sales order's amount is in foreign currency
            self.assertEqual(eur_order.amount_total, 60.0)

        # the report should show the amount in company currency
        report_line = self.env['sale.report'].sudo().search(
            [('order_id', '=', eur_order.id)])
        self.assertEqual(report_line.price_total, 20.0)

    def test_sale_report_company_currency(self):
        usd_pricelist = self.env['product.pricelist'].create({
            'name': 'Pricelist (USD)',
            'currency_id': self.company.currency_id.id,
        })

        usd_order = self.env['sale.order'].with_company(self.company).create({
            'partner_id': self.partner.id,
            'pricelist_id': usd_pricelist.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 1.0,
                }),
            ]
        })
        # the sales order's amount is in company currency
        self.assertEqual(usd_order.amount_total, 20.0)

        # the report should match the amount on the SO
        report_line = self.env['sale.report'].sudo().search(
            [('order_id', '=', usd_order.id)])
        self.assertEqual(report_line.price_total, 20.0)
