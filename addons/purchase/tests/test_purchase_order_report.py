# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo.tests import Form, tagged
from odoo.addons.account.tests.common import AccountTestCommon

@tagged('post_install', '-at_install')
class TestPurchaseOrderReport(AccountTestCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPurchaseOrderReport, cls).setUpClass()
        cls.partner_id = cls.env['res.partner'].create({'name': 'A Partner'})
        cls.product1 = cls.env['product.product'].create({'name': 'A First Product'})
        cls.product2 = cls.env['product.product'].create({'name': 'A Second Product'})
        cls.PurchaseReport = cls.env['purchase.report']
        cls.company_id = cls.env.ref('base.main_company')

    def test_00_purchase_order_report(self):
        uom_dozen = self.env.ref('uom.product_uom_dozen')

        eur_currency = self.env.ref('base.EUR')
        self.company_id.currency_id = self.env.ref('base.USD').id

        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': datetime.today(),
            'rate': 2.0,
            'currency_id': eur_currency.id,
        })
        po = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'currency_id': eur_currency.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 1.0,
                    'product_uom': uom_dozen.id,
                    'price_unit': 100.0,
                    'date_planned': datetime.today(),
                    'taxes_id': False,
                }),
                (0, 0, {
                    'name': self.product2.name,
                    'product_id': self.product2.id,
                    'product_qty': 1.0,
                    'product_uom': uom_dozen.id,
                    'price_unit': 200.0,
                    'date_planned': datetime.today(),
                    'taxes_id': False,
                }),
            ],
        })
        po.button_confirm()

        f = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        f.partner_id = po.partner_id
        f.purchase_id = po
        invoice = f.save()
        invoice.post()
        po.flush()

        res_product1 = self.PurchaseReport.search([
            ('order_id', '=', po.id), ('product_id', '=', self.product1.id)])

        # check that report will convert dozen to unit or not
        self.assertEqual(res_product1.qty_ordered, 12.0, 'UoM conversion is not working')
        # report should show in company currency (amount/rate) = (100/2)
        self.assertEqual(res_product1.price_total, 50.0, 'Currency conversion is not working')

        res_product2 = self.PurchaseReport.search([
            ('order_id', '=', po.id), ('product_id', '=', self.product2.id)])

        # Check that repost should show 6 unit of product
        self.assertEqual(res_product2.qty_ordered, 12.0, 'UoM conversion is not working')
        # report should show in company currency (amount/rate) = (200/2)
        self.assertEqual(res_product2.price_total, 100.0, 'Currency conversion is not working')
