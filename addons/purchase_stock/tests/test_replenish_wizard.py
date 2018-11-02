# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.stock.tests.common import TestStockCommon


class TestReplenishWizard(TestStockCommon):
    def setUp(self):
        super(TestReplenishWizard, self).setUp()
        self.vendor = self.env['res.partner'].create(dict(name='The Replenisher', supplier=True))
        self.product1_price = 500

        # Create a supplier info witch the previous vendor
        self.supplierinfo = self.env['product.supplierinfo'].create({
            'name': self.vendor.id,
            'price': self.product1_price,
        })

        # Create a product with the 'buy' route and
        # the 'supplierinfo' prevously created
        self.product1 = self.env['product.product'].create({
            'name': 'product a',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'seller_ids': [(4, self.supplierinfo.id, 0)],
            'route_ids': [(4, self.env.ref('purchase_stock.route_warehouse0_buy').id, 0)],
        })

        # Additional Values required by the replenish wizard
        self.uom_unit = self.env.ref('uom.product_uom_unit')
        self.wh = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)

    def test_replenish_buy_1(self):
        """ Set a quantity to replenish via the "Buy" route and check if
        a purchase order is created with the correct values
        """
        self.product_uom_qty = 42

        replenish_wizard = self.env['product.replenish'].create({
            'product_id': self.product1.id,
            'product_tmpl_id': self.product1.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'quantity': self.product_uom_qty,
            'warehouse_id': self.wh.id,
        })
        replenish_wizard.launch_replenishment()
        last_po_id = self.env['purchase.order'].search([
            ('origin', 'ilike', '%Manual Replenishment%'),
            ('partner_id', '=', self.vendor.id)
        ])[-1]
        self.assertTrue(last_po_id, 'Purchase Order not found')
        order_line = last_po_id.order_line.search([('product_id', '=', self.product1.id)])
        self.assertTrue(order_line, 'The product is not in the Purchase Order')
        self.assertEqual(order_line.product_qty, self.product_uom_qty, 'Quantities does not match')
        self.assertEqual(order_line.price_unit, self.product1_price, 'Prices does not match')
