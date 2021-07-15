# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import Form
from odoo.addons.stock_account.tests.test_stockvaluationlayer import TestStockValuationCommon


class TestSaleStockMargin(TestStockValuationCommon):
    #########
    # UTILS #
    #########

    def _create_sale_order(self):
        return self.env['sale.order'].create({
            'name': 'Sale order',
            'partner_id': self.env.ref('base.partner_admin').id,
            'partner_invoice_id': self.env.ref('base.partner_admin').id,
        })

    def _create_sale_order_line(self, sale_order, product, quantity, price_unit=0):
        return self.env['sale.order.line'].create({
            'name': 'Sale order',
            'order_id': sale_order.id,
            'price_unit': price_unit,
            'product_id': product.id,
            'product_uom_qty': quantity,
            'product_uom': self.env.ref('uom.product_uom_unit').id,
        })

    def _create_product(self):
        product_template = self.env['product.template'].create({
            'name': 'Super product',
            'type': 'product',
        })
        product_template.categ_id.property_cost_method = 'fifo'
        return product_template.product_variant_ids

    #########
    # TESTS #
    #########

    def test_sale_stock_margin_1(self):
        sale_order = self._create_sale_order()
        product = self._create_product()

        self._make_in_move(product, 2, 35)
        self._make_out_move(product, 1)

        order_line = self._create_sale_order_line(sale_order, product, 1, 50)
        sale_order.action_confirm()

        self.assertEqual(order_line.purchase_price, 35)
        self.assertEqual(sale_order.margin, 15)

        sale_order.picking_ids.move_lines.quantity_done = 1
        sale_order.picking_ids.button_validate()

        self.assertEqual(order_line.purchase_price, 35)
        self.assertEqual(order_line.margin, 15)
        self.assertEqual(sale_order.margin, 15)

    def test_sale_stock_margin_2(self):
        sale_order = self._create_sale_order()
        product = self._create_product()

        self._make_in_move(product, 2, 32)
        self._make_in_move(product, 5, 17)
        self._make_out_move(product, 1)

        order_line = self._create_sale_order_line(sale_order, product, 2, 50)
        sale_order.action_confirm()

        self.assertEqual(order_line.purchase_price, 32)
        self.assertAlmostEqual(sale_order.margin, 36)

        sale_order.picking_ids.move_lines.quantity_done = 2
        sale_order.picking_ids.button_validate()

        self.assertAlmostEqual(order_line.purchase_price, 24.5)
        self.assertAlmostEqual(order_line.margin, 51)
        self.assertAlmostEqual(sale_order.margin, 51)

    def test_sale_stock_margin_3(self):
        sale_order = self._create_sale_order()
        product = self._create_product()

        self._make_in_move(product, 2, 10)
        self._make_out_move(product, 1)

        order_line = self._create_sale_order_line(sale_order, product, 2, 20)
        sale_order.action_confirm()

        self.assertEqual(order_line.purchase_price, 10)
        self.assertAlmostEqual(sale_order.margin, 20)

        sale_order.picking_ids.move_lines.quantity_done = 1
        sale_order.picking_ids.button_validate()

        self.assertAlmostEqual(order_line.purchase_price, 10)
        self.assertAlmostEqual(order_line.margin, 20)
        self.assertAlmostEqual(sale_order.margin, 20)

    def test_sale_stock_margin_4(self):
        sale_order = self._create_sale_order()
        product = self._create_product()

        self._make_in_move(product, 2, 10)
        self._make_in_move(product, 1, 20)
        self._make_out_move(product, 1)

        order_line = self._create_sale_order_line(sale_order, product, 2, 20)
        sale_order.action_confirm()

        self.assertEqual(order_line.purchase_price, 10)
        self.assertAlmostEqual(sale_order.margin, 20)

        sale_order.picking_ids.move_lines.quantity_done = 1
        res = sale_order.picking_ids.button_validate()
        Form(self.env[res['res_model']].with_context(res['context'])).save().process()

        self.assertAlmostEqual(order_line.purchase_price, 15)
        self.assertAlmostEqual(order_line.margin, 10)
        self.assertAlmostEqual(sale_order.margin, 10)

    def test_sale_stock_margin_5(self):
        sale_order = self._create_sale_order()
        product_1 = self._create_product()
        product_2 = self._create_product()

        self._make_in_move(product_1, 2, 35)
        self._make_in_move(product_1, 1, 51)
        self._make_out_move(product_1, 1)

        self._make_in_move(product_2, 2, 17)
        self._make_in_move(product_2, 1, 11)
        self._make_out_move(product_2, 1)

        order_line_1 = self._create_sale_order_line(sale_order, product_1, 2, 60)
        order_line_2 = self._create_sale_order_line(sale_order, product_2, 4, 20)
        sale_order.action_confirm()

        self.assertAlmostEqual(order_line_1.purchase_price, 35)
        self.assertAlmostEqual(order_line_2.purchase_price, 17)
        self.assertAlmostEqual(order_line_1.margin, 25 * 2)
        self.assertAlmostEqual(order_line_2.margin, 3 * 4)
        self.assertAlmostEqual(sale_order.margin, 62)

        sale_order.picking_ids.move_lines[0].quantity_done = 2
        sale_order.picking_ids.move_lines[1].quantity_done = 3

        res = sale_order.picking_ids.button_validate()
        Form(self.env[res['res_model']].with_context(res['context'])).save().process()

        self.assertAlmostEqual(order_line_1.purchase_price, 43)       # (35 + 51) / 2
        self.assertAlmostEqual(order_line_2.purchase_price, 12.5)     # (17 + 11 + 11 + 11) / 4
        self.assertAlmostEqual(order_line_1.margin, 34)               # (60 - 43) * 2
        self.assertAlmostEqual(order_line_2.margin, 30)               # (20 - 12.5) * 4
        self.assertAlmostEqual(sale_order.margin, 64)
