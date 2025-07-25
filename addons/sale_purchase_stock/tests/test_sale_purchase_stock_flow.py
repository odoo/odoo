# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import Command, fields
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
        cls.mto_product_without_seller = cls.env['product.product'].create({
            'name': 'SuperProduct',
            'is_storable': True,
            'route_ids': [Command.set((cls.mto_route + cls.buy_route).ids)],
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
        # dest_address_id should only be present for dropshipping
        self.assertFalse(po.dest_address_id)

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
        self.assertEqual(so.delivery_count, 1)
        delivery = so.picking_ids
        # Both moves should have the procure_method set to 'make_to_order', as the products follow the MTO route
        self.assertEqual(delivery.move_ids.mapped('procure_method'), ['make_to_order', 'make_to_order'])
        # Since the products have two different vendors, two purchase orders should be created.
        self.assertEqual(so.purchase_order_count, 2)
        po_2 = self.env['purchase.order'].search([('partner_id', '=', vendor_2.id)])
        po_2.button_cancel()
        # As one PO has been canceled, one of the moves should switch to MTS, while the other should remain in MTO.
        self.assertEqual(delivery.move_ids.mapped('procure_method'), ['make_to_order', 'make_to_stock'])
        line_2 = so.order_line.filtered(lambda sol: sol.product_id == product_2)
        # Updating the SO line should trigger another delivery, as the product in the first picking is in MTS and not in MTO
        line_2.product_uom_qty = 0
        self.assertEqual(so.delivery_count, 2)
        self.assertRecordValues(delivery.move_ids, [
            {'product_id': product_1.id, 'product_uom_qty': 1.0},
            {'product_id': product_2.id, 'product_uom_qty': 1.0},
        ])
        self.assertRecordValues(so.picking_ids[1].move_ids, [
            {'product_id': product_2.id, 'product_uom_qty': 1.0},
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
        so.action_cancel()
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

    def test_two_step_delivery_forecast_after_first_picking(self):
        """ When a product is moved with 2-step delivery, the first of the two pickings associated
        with that delivery (upon completion) should have the actual physical location to which the
        product was delivered as its destination in `report.stock.quantity`: prior, irrespective of
        the move's state, it would have its location_dest_id and location_final_id coalesced. This
        meant that the location that the StockMove had actually moved product to was not
        necessarily the destination location reflected in the generated report row, which lead to
        an incorrect forecast.
        """
        wh = self.env.user._get_default_warehouse_id()
        wh.delivery_steps = 'pick_ship'
        product = self.mto_product
        in_move = self.env['stock.move'].create({
            'name': 'in move',
            'product_id': product.id,
            'product_uom_qty': 2,
            'product_uom': product.uom_id.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': wh.lot_stock_id.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        in_move._action_confirm()
        in_move._action_assign()
        in_move.move_line_ids.quantity = 2
        in_move.picked = True
        in_move._action_done()

        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [Command.create({'product_id': product.id,'product_uom_qty': 2})],
        })
        sale_order.action_confirm()
        pick_picking = sale_order.picking_ids[0]
        pick_picking.move_ids.quantity = 2
        pick_picking.button_validate()

        forecasted_qty = self.env['report.stock.quantity'].with_context(fill_temporal=False)._read_group(
            domain=[
                ('state', '=', 'forecast'),
                ('warehouse_id', '=', wh.id),
                ('product_tmpl_id', '=', product.product_tmpl_id.id),
                ('date', '=', fields.Date.today() - timedelta(days=20)),
            ],
            aggregates=['product_qty:sum'],
            groupby=['date:day', 'product_id'],
        )
        self.assertEqual(forecasted_qty[0][2], 0)

    def test_mtso_buy_without_supplier(self):
        self.mto_route.rule_ids.procure_method = "mts_else_mto"

        product = self.env['product.product'].create({
            'name': 'Test Product',
            'route_ids': [Command.set((self.mto_route + self.buy_route).ids)],
            'is_storable': True,
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [
                (0, 0, {'product_id': product.id, 'price_unit': 100}),
            ],
        })
        sale_order.action_confirm()
        self.assertFalse(sale_order.order_line.move_ids.move_orig_ids)
        self.assertEqual(sale_order.order_line.move_ids.state, 'confirmed')

    def test_purchase_order_uom(self):
        fuzzy_drink = self.env['product.product'].create({
            'name': 'Fuzzy Drink',
            'is_storable': True,
            'route_ids': [Command.set((self.mto_route + self.buy_route).ids)],
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'seller_ids': [Command.create({
                'partner_id': self.vendor.id,
                'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                'price': 1,
            }),
            Command.create({
                'partner_id': self.vendor.id,
                'product_uom_id': self.env.ref('uom.product_uom_pack_6').id,
                'min_qty': 2,
                'price': 5,
            })],
        })
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [Command.create({
                'name': fuzzy_drink.name,
                'product_id': fuzzy_drink.id,
                'product_uom_qty': 10,
                'product_uom_id': self.env.ref('uom.product_uom_unit').id,
            })],
        })
        so.action_confirm()
        po = so._get_purchase_orders()
        self.assertEqual(po.order_line.product_uom_id, self.env.ref('uom.product_uom_unit'))
        self.assertEqual(po.order_line.product_qty, 10)
        self.assertEqual(po.order_line.price_unit, 1)
        po.button_cancel()

        so = so.copy({
            'order_line': [Command.create({
                'name': fuzzy_drink.name,
                'product_id': fuzzy_drink.id,
                'product_uom_qty': 15,
                'product_uom_id': self.env.ref('uom.product_uom_unit').id,
            })]
        })
        so.action_confirm()
        po = so._get_purchase_orders()
        self.assertEqual(po.order_line.product_uom_id, self.env.ref('uom.product_uom_pack_6'))
        self.assertEqual(po.order_line.product_qty, 2.5)
        self.assertEqual(po.order_line.price_unit, 5)

    def test_reservation_on_mto_product_after_po_cancellation(self):
        """Test that a reservation can be made on an MTO product after its purchase order is cancelled.
        - Create a sale order with two MTO products: one with a seller and one without.
        - Confirm the SO: only the product with a vendor should trigger a purchase order.
        - Cancel the generated purchase order.
        - The MTO product should switch to MTS (Make to Stock), allowing reservation.
        """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [
                Command.create({
                    'product_id': self.mto_product.id,
                    'product_uom_qty': 1,
                }),
                Command.create({
                    'product_id': self.mto_product_without_seller.id,
                    'product_uom_qty': 1,
                }),
            ],
        })
        sale_order.action_confirm()
        self.assertEqual(sale_order.state, 'sale')
        self.assertEqual(sale_order.picking_ids.state, 'waiting')

        mto_move = sale_order.picking_ids.move_ids.filtered(lambda m: m.product_id == self.mto_product)
        self.assertEqual(mto_move.quantity, 0)
        self.assertEqual(mto_move.procure_method, 'make_to_order')
        # As the MTO product has no seller, it should be switched to MTS
        mto_move_without_seller = sale_order.picking_ids.move_ids - mto_move
        self.assertEqual(mto_move_without_seller.quantity, 0)
        self.assertEqual(mto_move_without_seller.procure_method, 'make_to_stock')
        # Cancel the purchase order related to the MTO product
        purchase_order = sale_order._get_purchase_orders()
        self.assertEqual(purchase_order.state, 'draft')
        purchase_order.button_cancel()
        self.assertEqual(purchase_order.state, 'cancel')
        # The MTO product should now be in MTS
        self.assertEqual(sale_order.picking_ids.move_ids.mapped('procure_method'), ['make_to_stock', 'make_to_stock'])
        # update the quantity on hand of the MTO product
        self.env['stock.quant']._update_available_quantity(self.mto_product, sale_order.picking_ids.move_ids.location_id, 1)
        sale_order.picking_ids.action_assign()
        self.assertEqual(mto_move.quantity, 1)
        self.assertEqual(mto_move.procure_method, 'make_to_stock')
