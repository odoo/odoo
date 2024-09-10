# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, Form
from odoo import Command


class TestSalePurchaseStockFlow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestSalePurchaseStockFlow, cls).setUpClass()
        cls.mto_route = cls.env.ref('stock.route_warehouse0_mto')
        cls.buy_route = cls.env.ref('purchase_stock.route_warehouse0_buy')
        cls.mto_route.active = True

        cls.customer_location = cls.env.ref('stock.stock_location_customers')

        cls.vendor = cls.env['res.partner'].create({'name': 'Super Vendor'})
        cls.customer = cls.env['res.partner'].create({'name': 'Super Customer'})

        cls.mto_product = cls.env['product.product'].create({
            'name': 'SuperProduct',
            'type': 'product',
            'route_ids': [(6, 0, (cls.mto_route + cls.buy_route).ids)],
            'seller_ids': [(0, 0, {
                'partner_id': cls.vendor.id,
            })],
        })

    def test_cancel_so_with_draft_po(self):
        """
        Sell a MTO+Buy product -> a PO is generated
        Cancel the SO -> an activity should be added to the PO
        """
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.env.user.partner_id
        with so_form.order_line.new() as line:
            line.product_id = self.mto_product
        so = so_form.save()
        so.action_confirm()

        po = self.env['purchase.order'].search([('partner_id', '=', self.vendor.id)])

        so._action_cancel()

        self.assertTrue(po.activity_ids)
        self.assertIn(so.name, po.activity_ids.note)

    def test_qty_delivered_with_mto_and_done_quantity_change(self):
        """
        MTO product P
        Sell 10 x P. On the delivery, set the done quantity to 12, validate and
        then set the done quantity to 10: the delivered qty of the SOL should
        be 10
        """
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {
                'name': self.mto_product.name,
                'product_id': self.mto_product.id,
                'product_uom_qty': 10,
                'product_uom': self.mto_product.uom_id.id,
                'price_unit': 1,
            })],
        })
        so.action_confirm()

        delivery = so.picking_ids.filtered(lambda p: p.location_dest_id == self.customer_location)
        sm = delivery.move_ids
        sm.move_line_ids = [(5, 0, 0), (0, 0, {
            'location_id': sm.location_id.id,
            'location_dest_id': sm.location_dest_id.id,
            'product_id': sm.product_id.id,
            'qty_done': 12,
            'company_id': sm.company_id.id,
            'product_uom_id': sm.product_uom.id,
            'picking_id': delivery.id,
        })]
        delivery.button_validate()

        self.assertEqual(delivery.state, 'done')
        self.assertEqual(so.order_line.qty_delivered, 12)

        sm.move_line_ids.qty_done = 10
        self.assertEqual(so.order_line.qty_delivered, 10)

    def test_decreasing_sol_qty_for_mto_product(self):
        """
        We have two MTO + Buy route products: product1 and product2.
        product1 has enough units on hand for the sale order but product2 does not.
        If we lower the SOL quantity for product2 it should merge the negative move and not create a return order.
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        product1, product2 = self.env['product.product'].create([
            {
                'name': 'product1',
                'uom_id': self.env.ref('uom.product_uom_unit').id,
                'type': 'product',
                'route_ids': [(6, 0, (self.mto_route + self.buy_route).ids)]
            },
            {
                'name': 'product2',
                'uom_id': self.env.ref('uom.product_uom_unit').id,
                'type': 'product',
                'route_ids': [(6, 0, (self.mto_route + self.buy_route).ids)]
            }
        ])
        self.env['stock.quant']._update_available_quantity(product1, warehouse.lot_stock_id, 10)
        products_vendor = self.env['res.partner'].create([
            {'name': 'product vendor'},
        ])
        self.env['product.supplierinfo'].create([
            {
                'product_id': product1.id,
                'partner_id': products_vendor.id,
                'price': 5,
            },
            {
                'product_id': product2.id,
                'partner_id': products_vendor.id,
                'price': 5,
            }
        ])

        so = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'warehouse_id': warehouse.id,
            'order_line': [
                Command.create({
                    'name': product1.name,
                    'product_id': product1.id,
                    'product_uom_qty': 1,
                }),
                Command.create({
                    'name': product2.name,
                    'product_id': product2.id,
                    'product_uom_qty': 3,
                })
            ]
        })

        so.action_confirm()
        so.order_line[1].product_uom_qty = 1
        self.assertEqual(so.picking_ids.move_ids[1].product_uom_qty, 1)
        self.assertEqual(so.delivery_count, 1)
