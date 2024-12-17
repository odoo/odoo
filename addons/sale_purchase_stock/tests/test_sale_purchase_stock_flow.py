# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import Form, TransactionCase


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
            'is_storable': True,
            'route_ids': [(6, 0, (cls.mto_route + cls.buy_route).ids)],
            'seller_ids': [(0, 0, {
                'partner_id': cls.vendor.id,
            })],
        })
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Other Warehouse',
            'code': 'OTH',
        })
        cls.mto_route.rule_ids.procure_method = "make_to_order"

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

    def test_sale_need_purchase_variants(self):
        """
        MTO+Buy product with two variants P1 and P2 with a different vendor.
        Create a SO with 2 lines, one for each variant: 2 PO should be created.
        """

        att_color = self.env['product.attribute'].create({
            'name': 'Color',
            'value_ids': [
                Command.create({'name': 'red', 'sequence': 1}),
                Command.create({'name': 'blue', 'sequence': 2}),
            ],
        })
        product_template = self.env['product.template'].create({
            'name': 'SuperProduct',
            'route_ids': [Command.set((self.mto_route + self.buy_route).ids)],
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': att_color.id,
                    'value_ids': att_color.value_ids.ids,
                }),
            ],
        })
        red_product, blue_product = product_template.product_variant_ids
        red_vendor, blue_vendor = self.env['res.partner'].create([
            {'name': 'Super red vendor'},
            {'name': 'Super blue vendor'},
        ])
        self.env['product.supplierinfo'].create([
            {
                'product_id': red_product.id,
                'partner_id': red_vendor.id,
                'price': 5,
            },
            {
                'product_id': blue_product.id,
                'partner_id': blue_vendor.id,
                'price': 10,
            },
        ])
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [
                Command.create({
                    'name': red_product.name,
                    'product_id': red_product.id,
                    'product_uom_qty': 2,
                    'price_unit': 20,
                }),
                Command.create({
                    'name': blue_product.name,
                    'product_id': blue_product.id,
                    'product_uom_qty': 3,
                    'price_unit': 30,
                }),
            ],
        })
        so.action_confirm()

        red_po = self.env['purchase.order'].search([('partner_id', '=', red_vendor.id)], limit=1)
        self.assertTrue(red_po)
        self.assertRecordValues(red_po.order_line, [{'product_id': red_product.id, 'product_uom_qty': 2, 'price_unit': 5}])
        blue_po = self.env['purchase.order'].search([('partner_id', '=', blue_vendor.id)], limit=1)
        self.assertTrue(blue_po)
        self.assertRecordValues(blue_po.order_line, [{'product_id': blue_product.id, 'product_uom_qty': 3, 'price_unit': 10}])

    def test_link_sale_purchase_mto_link_multi_step(self):
        self.warehouse.reception_steps = 'two_steps'
        sale = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [
                Command.create({
                    'name': self.mto_product.name,
                    'product_id': self.mto_product.id,
                    'product_uom_qty': 1,
                }),
            ],
            'warehouse_id': self.warehouse.id,
        })
        sale.action_confirm()
        self.assertEqual(sale.purchase_order_count, 1)
        purchase = sale._get_purchase_orders()
        purchase.button_confirm()

        receipt = purchase.picking_ids
        receipt.move_ids.write({'quantity': 1, 'picked': True})
        receipt._action_done()
        self.assertEqual(sale.purchase_order_count, 1)

    def test_mto_and_partial_cancel(self):
        """
        First, confirm a SO with two lines with the MTO + Buy routes (the products
        should not be available in stock). Put the quantity of the first SOL to 0
        then back to max. Then cancel the PO for the first product and decrease back
        the quantity of the related SOL to 0:
        - The delivery should be updated
        - There should not be any return picking
        """
        product_1 = self.mto_product
        vendor_2 = self.env['res.partner'].create({'name': 'Lovely Vendor'})
        product_2 = self.env['product.product'].create({
            'name': 'LovelyProduct',
            'is_storable': True,
            'route_ids': [Command.set((self.mto_route + self.buy_route).ids)],
            'seller_ids': [Command.create({
                'partner_id': vendor_2.id,
            })],
        })
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [
                Command.create({
                    'name': product_1.name,
                    'product_id': product_1.id,
                    'product_uom_qty': 1,
                    'price_unit': 10,
                }),
                Command.create({
                    'name': product_2.name,
                    'product_id': product_2.id,
                    'product_uom_qty': 1,
                    'price_unit': 20,
                }),
            ],
        })
        so.action_confirm()
        delivery = so.picking_ids
        po_2 = self.env['purchase.order'].search([('partner_id', '=', vendor_2.id)])
        po_2.button_cancel()
        line_2 = so.order_line.filtered(lambda sol: sol.product_id == product_2)
        line_2.product_uom_qty = 0
        self.assertEqual(delivery, so.picking_ids)
        self.assertRecordValues(delivery.move_ids, [
            {'product_id': product_1.id, 'product_uom_qty': 1.0},
            {'product_id': product_2.id, 'product_uom_qty': 0.0},
        ])

    def test_mto_cancel_reset_to_quotation_and_update(self):
        """
        Confirm a SO with an MTO + Buy routes line. Cancel the SO,
        reset it to quotation confirm it and decrease the quantity.

        The quantity of the second delivery should be updated accordingly.
        """
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [
                Command.create({
                    'name': self.mto_product.name,
                    'product_id': self.mto_product.id,
                    'product_uom_qty': 2,
                    'product_uom_id': self.mto_product.uom_id.id,
                    'price_unit': 10,
                }),
            ],
        })
        so.action_confirm()
        delivery = so.picking_ids
        self.assertRecordValues(delivery.move_ids, [
            {'product_id': self.mto_product.id, 'product_uom_qty': 2.0},
        ])
        so.with_context(disable_cancel_warning=True).action_cancel()
        self.assertEqual(delivery.state, 'cancel')
        so.action_draft()
        so.action_confirm()
        new_delivery = so.picking_ids - delivery
        self.assertEqual(len(new_delivery), 1)
        self.assertRecordValues(new_delivery.move_ids, [
            {'product_id': self.mto_product.id, 'product_uom_qty': 2.0},
        ])
        with Form(so) as so_form:
            with so_form.order_line.edit(0) as line:
                line.product_uom_qty = 1
        self.assertEqual(so.picking_ids, delivery | new_delivery)
        self.assertRecordValues(new_delivery.move_ids, [
            {'product_id': self.mto_product.id, 'product_uom_qty': 1.0},
        ])
