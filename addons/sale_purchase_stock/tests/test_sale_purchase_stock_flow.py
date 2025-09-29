# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import Command, fields
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
                    'product_uom': red_product.uom_id.id,
                    'price_unit': 20,
                }),
                Command.create({
                    'name': blue_product.name,
                    'product_id': blue_product.id,
                    'product_uom_qty': 3,
                    'product_uom': blue_product.uom_id.id,
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
            'type': 'product',
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
                    'product_uom': product_1.uom_id.id,
                    'price_unit': 10,
                }),
                Command.create({
                    'name': product_2.name,
                    'product_id': product_2.id,
                    'product_uom_qty': 1,
                    'product_uom': product_2.uom_id.id,
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
                    'product_uom': self.mto_product.uom_id.id,
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

    def test_products_availability_with_mto_purchased_product_from_interwarehouse_transfer(self):
        """
        For MTO and purchased products from a 3-step delivery warehouse (WH2) supplied by another 3-step delivery
        warehouse (WH1), confirmed SOs create 7 delivery orders and 1 PO. Delivery orders should have 2 OUT moves
        (WH1 -> WH2 and WH2 -> Customer) and both the IN and reserved move for WH2 should be the interwarehouse
        move (WH2/IN).
        """
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_multi_routes = self.env.ref('stock.group_adv_location')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id)]})
        self.env.user.write({'groups_id': [(4, grp_multi_routes.id)]})

        # Configure warehouse 1, 3 step delivery
        wh1 = self.env.ref('stock.warehouse0')
        wh1.code, wh1.delivery_steps = 'WH1', 'pick_pack_ship'
        # Create warehouse 2, 3 step delivery and resupplied from WH1
        wh2 = self.env['stock.warehouse'].create({
            'name': 'WH2',
            'code': 'WH2',
            'delivery_steps': 'pick_pack_ship',
            'resupply_wh_ids': [(6, 0, [wh1.id])]
        })
        # Route WH2: Supply Product from WH1, check Sale Order Line
        route = self.env['stock.route'].search([('supplied_wh_id', '=', wh2.id), ('supplier_wh_id', '=', wh1.id)])
        route.sale_selectable = True
        commitment_date = fields.Date.today() + timedelta(days=10)

        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {
                'name': self.mto_product.name,
                'product_id': self.mto_product.id,
                'product_uom_qty': 3,
                'product_uom': self.mto_product.uom_id.id,
                'route_id': route.id,
            })],
            'warehouse_id': wh2.id,
            'picking_policy': 'one',
            'commitment_date': commitment_date,
        })
        sale_order.action_confirm()
        pickings = sale_order.picking_ids

        # 7 pickings and 1 PO should have been created
        self.assertEqual(len(sale_order.picking_ids), 7)
        self.assertEqual(sale_order.purchase_order_count, 1)

        # Confirm PO
        purchase_order = self.env['purchase.order'].search([('origin', '=', sale_order.display_name)])
        purchase_order.button_confirm()

        # Both OUTS (WH1 -> WH2 and WH2 -> Customer) products availability should be the commitment date
        out_pickings = pickings.filtered(lambda p: "OUT" in p.name)
        wh2_in_picking = pickings.filtered(lambda p: "IN" in p.name)
        for out in out_pickings:
            self.assertEqual(out.products_availability, commitment_date.strftime('Exp %m/%d/%Y'))

        # Check forecast report, two lines should have been made
        report_lines = self.env['stock.forecasted_product_product'].with_context(warehouse=wh2.id).get_report_values(docids=self.mto_product.ids)['docs']['lines']
        line_1, line_2 = report_lines[0], report_lines[1]
        self.assertEqual(len(report_lines), 2)

        # Check that line one's in move and reserved move is the WH2/IN, and line two is In Transit move
        self.assertEqual(
            [line_1.get('document_in')['name'], line_1.get('document_out')['name'], line_1.get('reservation')['name']],
            [wh2_in_picking.name, sale_order.name, wh2_in_picking.name]
        )
        self.assertEqual(
            [line_2.get('document_in'), line_2.get('document_out'), line_2.get('in_transit')],
            [False, False, True]
        )
