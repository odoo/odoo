# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo.tests import Form
from odoo.addons.stock.tests.common2 import TestStockCommon


class TestMTOPropagation(TestStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        vendor = cls.env['res.partner'].create({
            'name': 'Roger'
        })

        seller = cls.env['product.supplierinfo'].create({
            'name': vendor.id,
            'price': 12.0,
        })
        cls.route_buy = cls.warehouse_1.buy_pull_id.route_id.id
        cls.route_mto = cls.warehouse_1.mto_pull_id.route_id.id

        cls.product_mto = cls.env['product.product'].create({
            'name': 'Muscadet',
            'type': 'product',
            'route_ids': [(6, 0, [cls.route_buy, cls.route_mto])],
            'seller_ids': [(6, 0, [seller.id])],
            'categ_id': cls.env.ref('product.product_category_all').id,
            'supplier_taxes_id': [(6, 0, [])],
        })

    def _create_sale_order(self):
        order = self.env['sale.order'].create({
            'partner_id': self.partner_1.id,
            'partner_invoice_id': self.partner_1.id,
            'partner_shipping_id': self.partner_1.id,
            'pricelist_id': self.env.ref('product.list0').id,
            'picking_policy': 'direct',
            'warehouse_id': self.warehouse_1.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_mto.name,
                    'product_id': self.product_mto.id,
                    'product_uom_qty': 5,
                    'product_uom': self.uom_unit.id,
                })
            ]
        })
        order.action_confirm()
        return order

    def test_basic_propagate_1(self):
        """ Create a sales order for mto product.

        Increase the quantity to sell should increase the quantity to buy as well
        as all the stock move quantities"""
        so = self._create_sale_order()

        po = so._get_purchase_orders()
        self.assertEqual(len(po), 1)
        # Increase quantity on SO
        so.write({'order_line': [(1, so.order_line[0].id, {'product_uom_qty': 8})]})
        out_move = so.picking_ids.move_lines
        self.assertEqual(out_move.product_uom_qty, 8)
        self.assertEqual(po.order_line.product_qty, 8)

    def test_basic_propagate_2(self):
        """ Create a sales order for mto product.

        Decrease the quantity to sell should decrease the quantity to buy as well
        as all the stock move quantities"""
        so = self._create_sale_order()

        po = so._get_purchase_orders()
        # Decrease quantity on SO
        so.write({'order_line': [(1, so.order_line[0].id, {'product_uom_qty': 3})]})
        out_move = so.picking_ids.move_lines
        self.assertEqual(out_move.product_uom_qty, 3)
        self.assertEqual(po.order_line.product_qty, 3)

    def test_basic_propagate_3(self):
        """ Create a sales order for mto product.

        Confirm the purchase order.
        Increase the quantity to sell should increase the quantity to buy as well
        as all the stock move quantities"""
        so = self._create_sale_order()

        po = so._get_purchase_orders()
        po.button_confirm()
        self.assertEqual(len(po.picking_ids.move_lines), 1)
        # Decrease quantity on SO
        so.write({'order_line': [(1, so.order_line[0].id, {'product_uom_qty': 8})]})
        pos = so._get_purchase_orders()
        self.assertEqual(len(pos), 2)
        out_move = so.picking_ids.move_lines
        self.assertEqual(len(pos.picking_ids.move_lines), 1)  # only one PO confirmed
        self.assertEqual(len(out_move), 2)
        self.assertEqual(sum(out_move.mapped('product_uom_qty')), 8)
        self.assertEqual(po.order_line.product_qty, 5)
        self.assertEqual(po.picking_ids.move_lines.product_uom_qty, 5)
        self.assertEqual(sum(pos.order_line.mapped('product_qty')), 8)

    def test_basic_propagate_4(self):
        """ Create a sales order for mto product.

        Confirm the purchase order.
        Decrease the quantity to sell should decrease the quantity to buy as well
        as all the stock move quantities"""
        so = self._create_sale_order()

        po = so._get_purchase_orders()
        po.button_confirm()
        # Decrease quantity on SO
        so.write({'order_line': [(1, so.order_line[0].id, {'product_uom_qty': 3})]})
        out_move = so.picking_ids.move_lines
        self.assertEqual(out_move.product_uom_qty, 3)
        self.assertEqual(po.order_line.product_qty, 5)
        self.assertEqual(po.picking_ids.move_lines.product_uom_qty, 3)

    def test_basic_propagate_5(self):
        """ Create a sales order for mto product.

        Confirm the purchase order.
        Increase the quantity to sell should increase the quantity to buy as well
        then decrease to the original value """
        so = self._create_sale_order()

        po = so._get_purchase_orders()
        po.button_confirm()
        # Decrease quantity on SO
        so.write({'order_line': [(1, so.order_line[0].id, {'product_uom_qty': 8})]})
        out_move = so.picking_ids.move_lines
        self.assertEqual(len(out_move), 2)
        self.assertEqual(out_move.mapped('product_uom_qty'), [5, 3])
        so.write({'order_line': [(1, so.order_line[0].id, {'product_uom_qty': 5})]})

        pos = so._get_purchase_orders()
        self.assertEqual(pos.mapped('state'), ['draft', 'purchase'])
        draft_po = pos.filtered(lambda p: p.state == 'draft')

        self.assertEqual(out_move.mapped('product_uom_qty'), [2, 3])
        self.assertEqual(po.order_line.product_qty, 5)
        self.assertEqual(draft_po.order_line.product_qty, 0)
