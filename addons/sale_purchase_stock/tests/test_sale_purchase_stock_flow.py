# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.fields import Date
from odoo.tools.date_utils import add
from odoo.tests.common import TransactionCase, Form


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
            'quantity': 12,
            'company_id': sm.company_id.id,
            'product_uom_id': sm.product_uom.id,
            'picking_id': delivery.id,
        })]
        delivery.button_validate()

        self.assertEqual(delivery.state, 'done')
        self.assertEqual(delivery.move_ids.move_line_ids.quantity, 12)
        self.assertEqual(so.order_line.qty_delivered, 12)

        sm.move_line_ids.quantity = 10
        self.assertEqual(so.order_line.qty_delivered, 10)

    def test_auto_trigger_snoozed_orderpoint(self):
        """ Check that reordering rules are auto triggerred unless they are snoozed """

        seller = self.env['product.supplierinfo'].create({
            'partner_id': self.vendor.id,
            'price': 10,
        })
        product = self.env['product.product'].create({
            'name': 'Super product 1',
            'type': 'product',
            'seller_ids': [Command.set(seller.ids)],
            'route_ids': [Command.set(self.buy_route.ids)],
        })
        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'name': 'Super product RR',
            'route_id': self.buy_route.id,
            'product_id': product.id,
            'product_min_qty': 0,
            'product_max_qty': 5,
        })
        so_1, so_2 = self.env['sale.order'].create([
            {
                'partner_id': self.customer.id,
                'order_line': [Command.create({
                    'name': product.name,
                    'product_id': product.id,
                    'product_uom_qty': 1,
                    'product_uom': product.uom_id.id,
                    'price_unit': product.list_price,
                })]
            },
            {
                'partner_id': self.customer.id,
                'order_line': [Command.create({
                    'name': product.name,
                    'product_id': product.id,
                    'product_uom_qty': 2,
                    'product_uom': product.uom_id.id,
                    'price_unit': product.list_price,
                })]
            },
        ])

        # we check that the first so triggers the RR
        so_1.action_confirm()
        po = self.env['purchase.order'].search([('partner_id', '=', self.vendor.id)], limit=1)
        self.assertEqual(po.order_line.product_qty, 6.0)
        po.button_cancel()
        self.assertEqual(po.state, "cancel")

        # we snooze the RR and check that the second so does not trigger it
        orderpoint.snoozed_until = add(Date.today(), days=1)
        so_2.action_confirm()
        po = self.env['purchase.order'].search([('partner_id', '=', self.vendor.id), ('state', '!=', 'cancel')], limit=1)
        self.assertFalse(po)
