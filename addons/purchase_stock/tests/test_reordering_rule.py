# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime as dt, time
from datetime import timedelta as td
from freezegun import freeze_time

from odoo import SUPERUSER_ID
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
@freeze_time("2021-01-14 09:12:15")
class TestReorderingRule(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestReorderingRule, cls).setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Smith'
        })

        # create product and set the vendor
        product_form = Form(cls.env['product.product'])
        product_form.name = 'Product A'
        product_form.detailed_type = 'product'
        product_form.description = 'Internal Notes'
        with product_form.seller_ids.new() as seller:
            seller.partner_id = cls.partner
        product_form.route_ids.add(cls.env.ref('purchase_stock.route_warehouse0_buy'))
        cls.product_01 = product_form.save()

    def test_reordering_rule_1(self):
        """
            - Receive products in 2 steps
            - The product has a reordering rule
            - On the po generated, the source document should be the name of the reordering rule
            - Increase the quantity on the RFQ, the extra quantity should follow the push rules
            - Increase the quantity on the PO, the extra quantity should follow the push rules
            - There should be one move supplier -> input and two moves input -> stock
        """
        warehouse_1 = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        warehouse_1.write({'reception_steps': 'two_steps'})
        warehouse_2 = self.env['stock.warehouse'].create({'name': 'WH 2', 'code': 'WH2', 'company_id': self.env.company.id, 'partner_id': self.env.company.partner_id.id, 'reception_steps': 'one_step'})

        # Create and set specific buyer for partner
        buyer_id = self.env['res.users'].create({
            'login': 'buyer1',
            'name': 'Buyer1',
            'email': 'buyer1@example.com',
        })
        self.partner.buyer_id = buyer_id.id

        # create reordering rule
        orderpoint_form = Form(self.env['stock.warehouse.orderpoint'])
        orderpoint_form.warehouse_id = warehouse_1
        orderpoint_form.location_id = warehouse_1.lot_stock_id
        orderpoint_form.product_id = self.product_01
        orderpoint_form.product_min_qty = 0.000
        orderpoint_form.product_max_qty = 0.000
        order_point = orderpoint_form.save()
        # Create Delivery Order of 10 product
        picking_form = Form(self.env['stock.picking'])
        picking_form.partner_id = self.partner
        picking_form.picking_type_id = self.env.ref('stock.picking_type_out')
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product_01
            move.product_uom_qty = 10.0
        customer_picking = picking_form.save()
        customer_picking.action_confirm()
        # Run scheduler
        self.env['procurement.group'].run_scheduler()

        # Check purchase order created or not
        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.partner.id)])
        self.assertTrue(purchase_order, 'No purchase order created.')

        # Check the picking type on the purchase order
        purchase_order.picking_type_id = warehouse_2.in_type_id
        with self.assertRaises(UserError):
            purchase_order.button_confirm()
        purchase_order.picking_type_id = warehouse_1.in_type_id

        # On the po generated, the source document should be the name of the reordering rule
        self.assertEqual(order_point.name, purchase_order.origin, 'Source document on purchase order should be the name of the reordering rule.')
        self.assertEqual(purchase_order.order_line.product_qty, 10)
        self.assertEqual(purchase_order.order_line.name, 'Product A')
        self.assertEqual(purchase_order.user_id, buyer_id)

        # Increase the quantity on the RFQ before confirming it
        purchase_order.order_line.product_qty = 12
        purchase_order.button_confirm()

        self.assertEqual(purchase_order.picking_ids.move_ids.filtered(lambda m: m.product_id == self.product_01).product_qty, 12)
        next_picking = purchase_order.picking_ids.move_ids.move_dest_ids.picking_id
        self.assertEqual(len(next_picking), 2)
        self.assertEqual(next_picking[0].move_ids.filtered(lambda m: m.product_id == self.product_01).product_qty, 10)
        self.assertEqual(next_picking[1].move_ids.filtered(lambda m: m.product_id == self.product_01).product_qty, 2)

        # Increase the quantity on the PO
        purchase_order.order_line.product_qty = 15
        self.assertEqual(purchase_order.picking_ids.move_ids.product_qty, 15)
        self.assertEqual(next_picking[0].move_ids.filtered(lambda m: m.product_id == self.product_01).product_qty, 10)
        self.assertEqual(next_picking[1].move_ids.filtered(lambda m: m.product_id == self.product_01).product_qty, 5)

    def test_reordering_rule_2(self):
        """
            - Receive products in 1 steps
            - The product has two reordering rules, each one applying in a sublocation
            - Processing the purchase order should fulfill the two sublocations
            - Increase the quantity on the RFQ for one of the POL, the extra quantity will go to
              the original subloc since we don't know where to push it (no move dest)
            - Increase the quantity on the PO, the extra quantity should follow the push rules and
              thus go to stock
        """
        # Required for `warehouse_id` to be visible in the view
        self.env.user.groups_id += self.env.ref('stock.group_stock_multi_locations')
        warehouse_1 = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        subloc_1 = self.env['stock.location'].create({'name': 'subloc_1', 'location_id': warehouse_1.lot_stock_id.id})
        subloc_2 = self.env['stock.location'].create({'name': 'subloc_2', 'location_id': warehouse_1.lot_stock_id.id})

        # create reordering rules
        orderpoint_form = Form(self.env['stock.warehouse.orderpoint'])
        orderpoint_form.warehouse_id = warehouse_1
        orderpoint_form.location_id = subloc_1
        orderpoint_form.product_id = self.product_01
        orderpoint_form.product_min_qty = 0.000
        orderpoint_form.product_max_qty = 0.000
        order_point_1 = orderpoint_form.save()
        orderpoint_form = Form(self.env['stock.warehouse.orderpoint'])
        orderpoint_form.warehouse_id = warehouse_1
        orderpoint_form.location_id = subloc_2
        orderpoint_form.product_id = self.product_01
        orderpoint_form.product_min_qty = 0.000
        orderpoint_form.product_max_qty = 0.000
        order_point_2 = orderpoint_form.save()

        # Create Delivery Order of 10 product
        picking_form = Form(self.env['stock.picking'])
        picking_form.partner_id = self.partner
        picking_form.picking_type_id = self.env.ref('stock.picking_type_out')
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product_01
            move.product_uom_qty = 10.0
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product_01
            move.product_uom_qty = 10.0
        customer_picking = picking_form.save()
        customer_picking.move_ids[0].location_id = subloc_1.id
        customer_picking.move_ids[1].location_id = subloc_2.id

        # picking confirm
        customer_picking.action_confirm()
        self.assertEqual(self.product_01.with_context(location=subloc_1.id).virtual_available, -10)
        self.assertEqual(self.product_01.with_context(location=subloc_2.id).virtual_available, -10)

        # Run scheduler
        self.env['procurement.group'].run_scheduler()

        # Check purchase order created or not
        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.partner.id)])
        self.assertTrue(purchase_order, 'No purchase order created.')
        self.assertEqual(len(purchase_order.order_line), 2, 'Not enough purchase order lines created.')

        # increment the qty of the first po line
        purchase_order.order_line.filtered(lambda pol: pol.orderpoint_id == order_point_1).product_qty = 15
        purchase_order.button_confirm()
        self.assertEqual(self.product_01.with_context(location=subloc_1.id).virtual_available, 5)
        self.assertEqual(self.product_01.with_context(location=subloc_2.id).virtual_available, 0)

        # increment the qty of the second po line
        purchase_order.order_line.filtered(lambda pol: pol.orderpoint_id == order_point_2).with_context(debug=True).product_qty = 15
        self.assertEqual(self.product_01.with_context(location=subloc_1.id).virtual_available, 5)
        self.assertEqual(self.product_01.with_context(location=subloc_2.id).virtual_available, 0)
        self.assertEqual(self.product_01.with_context(location=warehouse_1.lot_stock_id.id).virtual_available, 10)  # 5 on the main loc, 5 on subloc_1

        self.assertEqual(purchase_order.picking_ids.move_ids[-1].product_qty, 5)
        self.assertEqual(purchase_order.picking_ids.move_ids[-1].location_dest_id, warehouse_1.lot_stock_id)

    def test_reordering_rule_3(self):
        """
            trigger a reordering rule with a route to a location without warehouse
        """
        warehouse_1 = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)

        outside_loc = self.env['stock.location'].create({
            'name': 'outside',
            'usage': 'internal',
            'location_id': self.env.ref('stock.stock_location_locations').id,
        })
        route = self.env['stock.route'].create({
            'name': 'resupply outside',
            'rule_ids': [
                (0, False, {
                    'name': 'Buy',
                    'location_dest_id': warehouse_1.lot_stock_id.id,
                    'company_id': self.env.company.id,
                    'action': 'buy',
                    'sequence': 2,
                    'procure_method': 'make_to_stock',
                    'picking_type_id': self.env.ref('stock.picking_type_in').id,
                }),
                (0, False, {
                    'name': 'ressuply from stock',
                    'location_src_id': warehouse_1.lot_stock_id.id,
                    'location_dest_id': outside_loc.id,
                    'company_id': self.env.company.id,
                    'action': 'pull',
                    'procure_method': 'mts_else_mto',
                    'sequence': 1,
                    'picking_type_id': self.env.ref('stock.picking_type_out').id,
                }),
            ],
        })
        vendor1 = self.env['res.partner'].create({'name': 'AAA', 'email': 'from.test@example.com'})
        supplier_info1 = self.env['product.supplierinfo'].create({
            'partner_id': vendor1.id,
            'price': 50,
        })
        product = self.env['product.product'].create({
            'name': 'product_rr_3',
            'type': 'product',
            'route_ids': [(4, route.id)],
            'seller_ids': [(6, 0, [supplier_info1.id])],
        })

        # create reordering rules
        # Required for `warehouse_id` to be visible in the view
        self.env['res.users'].browse(2).groups_id += self.env.ref('stock.group_stock_multi_locations')
        orderpoint_form = Form(self.env['stock.warehouse.orderpoint'].with_user(2))
        orderpoint_form.warehouse_id = warehouse_1
        orderpoint_form.location_id = outside_loc
        orderpoint_form.product_id = product
        orderpoint_form.product_min_qty = 0.000
        orderpoint_form.product_max_qty = 0.000
        order_point_1 = orderpoint_form.save()
        order_point_1.route_id = route
        order_point_1.trigger = 'manual'

        # Create move out of 10 product
        move = self.env['stock.move'].create({
            'name': 'move out',
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 10,
            'location_id': outside_loc.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move._action_confirm()

        # Forecast on the order point should be -10
        self.assertEqual(order_point_1.qty_forecast, -10)

        order_point_1.action_replenish()

        # Check purchase order created or not
        purchase_order = self.env['purchase.order.line'].search([('product_id', '=', product.id)]).order_id
        self.assertTrue(purchase_order, 'No purchase order created.')
        self.assertEqual(len(purchase_order.order_line), 1, 'Not enough purchase order lines created.')
        purchase_order.button_confirm()

    def test_reordering_rule_triggered_two_times(self):
        """
        A product P wth RR 0-0-1.
        Confirm a delivery with 1 x P -> PO created for it.
        Confirm a second delivery, with 1 x P again:
        - The PO should be updated
        - The qty to order of the RR should be zero
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        stock_location = warehouse.lot_stock_id
        out_type = warehouse.out_type_id
        customer_location = self.env.ref('stock.stock_location_customers')

        rr = self.env['stock.warehouse.orderpoint'].create({
            'location_id': stock_location.id,
            'product_id': self.product_01.id,
            'product_min_qty': 0,
            'product_max_qty': 0,
            'qty_multiple': 1,
        })

        delivery = self.env['stock.picking'].create({
            'picking_type_id': out_type.id,
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'move_ids': [(0, 0, {
                'name': self.product_01.name,
                'product_id': self.product_01.id,
                'product_uom_qty': 1,
                'product_uom': self.product_01.uom_id.id,
                'location_id': stock_location.id,
                'location_dest_id': customer_location.id,
            })]
        })
        delivery.action_confirm()

        pol = self.env['purchase.order.line'].search([('product_id', '=', self.product_01.id)])
        self.assertEqual(pol.product_qty, 1.0)
        self.assertEqual(rr.qty_to_order, 0.0)

        delivery = self.env['stock.picking'].create({
            'picking_type_id': out_type.id,
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'move_ids': [(0, 0, {
                'name': self.product_01.name,
                'product_id': self.product_01.id,
                'product_uom_qty': 1,
                'product_uom': self.product_01.uom_id.id,
                'location_id': stock_location.id,
                'location_dest_id': customer_location.id,
            })]
        })
        delivery.action_confirm()

        self.assertEqual(pol.product_qty, 2.0)
        self.assertEqual(rr.qty_to_order, 0.0)

    def test_replenish_report_1(self):
        """Tests the auto generation of manual orderpoints.

        Opening multiple times the report should not duplicate the generated orderpoints.
        MTO products should not trigger the creation of generated orderpoints
        """
        partner = self.env['res.partner'].create({
            'name': 'Tintin'
        })
        route_buy = self.env.ref('purchase_stock.route_warehouse0_buy')
        route_mto = self.env.ref('stock.route_warehouse0_mto')

        product_form = Form(self.env['product.product'])
        product_form.name = 'Simple Product'
        product_form.detailed_type = 'product'
        with product_form.seller_ids.new() as s:
            s.partner_id = partner
        product = product_form.save()

        product_form = Form(self.env['product.product'])
        product_form.name = 'Product BUY + MTO'
        product_form.detailed_type = 'product'
        product_form.route_ids.add(route_buy)
        product_form.route_ids.add(route_mto)
        with product_form.seller_ids.new() as s:
            s.partner_id = partner
        product_buy_mto = product_form.save()

        # Create Delivery Order of 20 product and 10 buy + MTO
        picking_form = Form(self.env['stock.picking'])
        picking_form.partner_id = partner
        picking_form.picking_type_id = self.env.ref('stock.picking_type_out')
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product
            move.product_uom_qty = 10.0
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product
            move.product_uom_qty = 10.0
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product_buy_mto
            move.product_uom_qty = 10.0
        customer_picking = picking_form.save()
        customer_picking.move_ids.filtered(lambda m: m.product_id == product_buy_mto).procure_method = 'make_to_order'
        customer_picking.action_confirm()
        self.env['stock.warehouse.orderpoint']._get_orderpoint_action()
        self.env['stock.warehouse.orderpoint']._get_orderpoint_action()

        orderpoint_product = self.env['stock.warehouse.orderpoint'].search(
            [('product_id', '=', product.id)])
        orderpoint_product_mto_buy = self.env['stock.warehouse.orderpoint'].search(
            [('product_id', '=', product_buy_mto.id)])
        self.assertFalse(orderpoint_product_mto_buy)
        self.assertEqual(len(orderpoint_product), 1.0)
        self.assertEqual(orderpoint_product.qty_to_order, 20.0)
        self.assertEqual(orderpoint_product.trigger, 'manual')
        self.assertEqual(orderpoint_product.create_uid.id, SUPERUSER_ID)

        orderpoint_product.action_replenish()
        po = self.env['purchase.order'].search([('partner_id', '=', partner.id)])
        self.assertTrue(po)
        self.assertEqual(len(po.order_line), 2.0)
        po_line_product_mto = po.order_line.filtered(lambda l: l.product_id == product_buy_mto)
        po_line_product = po.order_line.filtered(lambda l: l.product_id == product)
        self.assertEqual(po_line_product_mto.product_uom_qty, 10.0)
        self.assertEqual(po_line_product.product_uom_qty, 20.0)

        self.env['stock.warehouse.orderpoint']._get_orderpoint_action()
        orderpoint_product = self.env['stock.warehouse.orderpoint'].search(
            [('product_id', '=', product.id)])
        orderpoint_product_mto_buy = self.env['stock.warehouse.orderpoint'].search(
            [('product_id', '=', product_buy_mto.id)])
        self.assertFalse(orderpoint_product)
        self.assertFalse(orderpoint_product_mto_buy)

        # Create Delivery Order of 10 product and 10 buy + MTO
        picking_form = Form(self.env['stock.picking'])
        picking_form.partner_id = partner
        picking_form.picking_type_id = self.env.ref('stock.picking_type_out')
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product
            move.product_uom_qty = 10.0
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product_buy_mto
            move.product_uom_qty = 10.0
        customer_picking = picking_form.save()
        customer_picking.move_ids.filtered(lambda m: m.product_id == product_buy_mto).procure_method = 'make_to_order'
        customer_picking.action_confirm()
        self.env['stock.warehouse.orderpoint'].flush_model()

        self.env['stock.warehouse.orderpoint']._get_orderpoint_action()
        orderpoint_product = self.env['stock.warehouse.orderpoint'].search(
            [('product_id', '=', product.id)])
        orderpoint_product_mto_buy = self.env['stock.warehouse.orderpoint'].search(
            [('product_id', '=', product_buy_mto.id)])
        self.assertFalse(orderpoint_product_mto_buy)
        self.assertEqual(len(orderpoint_product), 1.0)
        self.assertEqual(orderpoint_product.qty_to_order, 10.0)
        self.assertEqual(orderpoint_product.trigger, 'manual')
        self.assertEqual(orderpoint_product.create_uid.id, SUPERUSER_ID)

    def test_replenish_report_2(self):
        """Same then `test_replenish_report_1` but with two steps receipt enabled"""
        partner = self.env['res.partner'].create({
            'name': 'Tintin'
        })
        for wh in self.env['stock.warehouse'].search([]):
            wh.write({'reception_steps': 'two_steps'})
        route_buy = self.env.ref('purchase_stock.route_warehouse0_buy')
        route_mto = self.env.ref('stock.route_warehouse0_mto')

        product_form = Form(self.env['product.product'])
        product_form.name = 'Simple Product'
        product_form.detailed_type = 'product'
        with product_form.seller_ids.new() as s:
            s.partner_id = partner
        product = product_form.save()

        product_form = Form(self.env['product.product'])
        product_form.name = 'Product BUY + MTO'
        product_form.detailed_type = 'product'
        product_form.route_ids.add(route_buy)
        product_form.route_ids.add(route_mto)
        with product_form.seller_ids.new() as s:
            s.partner_id = partner
        product_buy_mto = product_form.save()

        # Create Delivery Order of 20 product and 10 buy + MTO
        picking_form = Form(self.env['stock.picking'])
        picking_form.partner_id = partner
        picking_form.picking_type_id = self.env.ref('stock.picking_type_out')
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product
            move.product_uom_qty = 10.0
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product
            move.product_uom_qty = 10.0
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product_buy_mto
            move.product_uom_qty = 10.0
        customer_picking = picking_form.save()
        customer_picking.move_ids.filtered(lambda m: m.product_id == product_buy_mto).procure_method = 'make_to_order'
        customer_picking.action_confirm()
        self.env['stock.warehouse.orderpoint']._get_orderpoint_action()
        orderpoint_product = self.env['stock.warehouse.orderpoint'].search(
            [('product_id', '=', product.id)])
        orderpoint_product_mto_buy = self.env['stock.warehouse.orderpoint'].search(
            [('product_id', '=', product_buy_mto.id)])
        self.assertFalse(orderpoint_product_mto_buy)
        self.assertEqual(len(orderpoint_product), 1.0)
        self.assertEqual(orderpoint_product.qty_to_order, 20.0)
        self.assertEqual(orderpoint_product.trigger, 'manual')
        self.assertEqual(orderpoint_product.create_uid.id, SUPERUSER_ID)

        orderpoint_product.action_replenish()
        po = self.env['purchase.order'].search([('partner_id', '=', partner.id)])
        self.assertTrue(po)
        self.assertEqual(len(po.order_line), 2.0)
        po_line_product_mto = po.order_line.filtered(lambda l: l.product_id == product_buy_mto)
        po_line_product = po.order_line.filtered(lambda l: l.product_id == product)
        self.assertEqual(po_line_product_mto.product_uom_qty, 10.0)
        self.assertEqual(po_line_product.product_uom_qty, 20.0)

        self.env['stock.warehouse.orderpoint'].flush_model()
        self.env['stock.warehouse.orderpoint']._get_orderpoint_action()
        orderpoint_product = self.env['stock.warehouse.orderpoint'].search(
            [('product_id', '=', product.id)])
        orderpoint_product_mto_buy = self.env['stock.warehouse.orderpoint'].search(
            [('product_id', '=', product_buy_mto.id)])
        self.assertFalse(orderpoint_product)
        self.assertFalse(orderpoint_product_mto_buy)

        # Create Delivery Order of 10 product and 10 buy + MTO
        picking_form = Form(self.env['stock.picking'])
        picking_form.partner_id = partner
        picking_form.picking_type_id = self.env.ref('stock.picking_type_out')
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product
            move.product_uom_qty = 10.0
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product_buy_mto
            move.product_uom_qty = 10.0
        customer_picking = picking_form.save()
        customer_picking.move_ids.filtered(lambda m: m.product_id == product_buy_mto).procure_method = 'make_to_order'
        customer_picking.action_confirm()
        self.env['stock.warehouse.orderpoint'].flush_model()

        self.env['stock.warehouse.orderpoint']._get_orderpoint_action()
        orderpoint_product = self.env['stock.warehouse.orderpoint'].search(
            [('product_id', '=', product.id)])
        orderpoint_product_mto_buy = self.env['stock.warehouse.orderpoint'].search(
            [('product_id', '=', product_buy_mto.id)])
        self.assertFalse(orderpoint_product_mto_buy)
        self.assertEqual(len(orderpoint_product), 1.0)
        self.assertEqual(orderpoint_product.qty_to_order, 10.0)
        self.assertEqual(orderpoint_product.trigger, 'manual')
        self.assertEqual(orderpoint_product.create_uid.id, SUPERUSER_ID)

    def test_procure_not_default_partner(self):
        """Define a product with 2 vendors. First run a "standard" procurement,
        default vendor should be used. Then, call a procurement with
        `partner_id` specified in values, the specified vendor should be
        used."""
        purchase_route = self.env.ref("purchase_stock.route_warehouse0_buy")
        uom_unit = self.env.ref("uom.product_uom_unit")
        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1)
        product = self.env["product.product"].create({
            "name": "product TEST",
            "standard_price": 100.0,
            "type": "product",
            "uom_id": uom_unit.id,
            "default_code": "A",
            "route_ids": [(6, 0, purchase_route.ids)],
        })
        default_vendor = self.env["res.partner"].create({
            "name": "Supplier A",
        })
        secondary_vendor = self.env["res.partner"].create({
            "name": "Supplier B",
        })
        self.env["product.supplierinfo"].create({
            "partner_id": default_vendor.id,
            "product_tmpl_id": product.product_tmpl_id.id,
            "delay": 7,
        })
        self.env["product.supplierinfo"].create({
            "partner_id": secondary_vendor.id,
            "product_tmpl_id": product.product_tmpl_id.id,
            "delay": 10,
        })

        # Test standard procurement.
        po_line = self.env["purchase.order.line"].search(
            [("product_id", "=", product.id)])
        self.assertFalse(po_line)
        self.env["procurement.group"].run(
            [self.env["procurement.group"].Procurement(
                product, 100, uom_unit,
                warehouse.lot_stock_id, "Test default vendor", "/",
                self.env.company,
                {
                    "warehouse_id": warehouse,
                    "date_planned": dt.today() + td(days=15),
                    "rule_id": warehouse.buy_pull_id,
                    "group_id": False,
                    "route_ids": [],
                }
            )])
        po_line = self.env["purchase.order.line"].search(
            [("product_id", "=", product.id)])
        self.assertTrue(po_line)
        self.assertEqual(po_line.partner_id, default_vendor)
        po_line.order_id.button_cancel()
        po_line.order_id.unlink()

        # now force the vendor:
        po_line = self.env["purchase.order.line"].search(
            [("product_id", "=", product.id)])
        self.assertFalse(po_line)
        self.env["procurement.group"].run(
            [self.env["procurement.group"].Procurement(
                product, 100, uom_unit,
                warehouse.lot_stock_id, "Test default vendor", "/",
                self.env.company,
                {
                    "warehouse_id": warehouse,
                    "date_planned": dt.today() + td(days=15),
                    "rule_id": warehouse.buy_pull_id,
                    "group_id": False,
                    "route_ids": [],
                    "supplierinfo_name": secondary_vendor,
                }
            )])
        po_line = self.env["purchase.order.line"].search(
            [("product_id", "=", product.id)])
        self.assertTrue(po_line)
        self.assertEqual(po_line.partner_id, secondary_vendor)

    def test_procure_multi_lingual(self):
        """
        Define a product with description in English and French.
        Run a procurement specifying a group_id with a partner (customer)
        set up with French as language.  Verify that the PO is generated
        using the default (English) language.
        """
        purchase_route = self.env.ref("purchase_stock.route_warehouse0_buy")
        # create a new warehouse to make sure it gets the mts/mto rule
        warehouse = self.env['stock.warehouse'].create({
            "name": "test warehouse",
            "active": True,
            'reception_steps': 'one_step',
            'delivery_steps': 'ship_only',
            'code': 'TEST'
        })
        customer_loc, _ = warehouse._get_partner_locations()
        mto_rule = self.env['stock.rule'].search(
            [('warehouse_id', '=', warehouse.id),
             ('procure_method', '=', 'mts_else_mto'),
             ('location_dest_id', '=', customer_loc.id)
            ]
        )
        route_mto = self.env["stock.route"].create({
            "name": "MTO",
            "active": True,
            "sequence": 3,
            "product_selectable": True,
            "rule_ids": [(6, 0, [
                mto_rule.id
            ])]
        })
        uom_unit = self.env.ref("uom.product_uom_unit")
        product = self.env["product.product"].create({
            "name": "product TEST",
            "standard_price": 100.0,
            "type": "product",
            "uom_id": uom_unit.id,
            "default_code": "A",
            "route_ids": [(6, 0, [
                route_mto.id,
                purchase_route.id,
            ])],
        })
        self.env['res.lang']._activate_lang('fr_FR')
        product.product_tmpl_id.with_context(lang='fr_FR').name = 'produit en français'
        product.with_context(lang='fr_FR').name = 'produit en français'
        default_vendor = self.env["res.partner"].create({
            "name": "Supplier A",
        })
        self.env["product.supplierinfo"].create({
            "partner_id": default_vendor.id,
            "product_tmpl_id": product.product_tmpl_id.id,
            "delay": 7,
        })
        customer = self.env["res.partner"].create({
            "name": "Customer",
            "lang": "fr_FR"
        })
        proc_group = self.env["procurement.group"].create({
            "partner_id": customer.id
        })
        procurement = self.env["procurement.group"].Procurement(
                product, 100, uom_unit,
                customer.property_stock_customer,
                "Test default vendor",
                "/",
                self.env.company,
                {
                    "warehouse_id": warehouse,
                    "date_planned": dt.today() + td(days=15),
                    "group_id": proc_group,
                    "route_ids": [],
                }
            )
        self.env.invalidate_all()

        self.env["procurement.group"].run([procurement])

        po_line = self.env["purchase.order.line"].search(
            [("product_id", "=", product.id)])
        self.assertTrue(po_line)
        self.assertEqual("[A] product TEST", po_line.name)

    def test_multi_locations_and_reordering_rule(self):
        """
        Suppose two orderpoints for the same product, each one to a different location
        If the user triggers each orderpoint separately, it should still produce two
        different purchase order lines (one for each orderpoint)
        """
        # Required for `warehouse_id` to be visible in the view
        self.env.user.groups_id += self.env.ref('stock.group_stock_multi_locations')
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1)
        stock_location = warehouse.lot_stock_id
        sub_location = self.env['stock.location'].create({'name': 'subloc_1', 'location_id': stock_location.id})

        orderpoint_form = Form(self.env['stock.warehouse.orderpoint'])
        orderpoint_form.warehouse_id = warehouse
        orderpoint_form.location_id = stock_location
        orderpoint_form.product_id = self.product_01
        orderpoint_form.product_min_qty = 1
        orderpoint_form.product_max_qty = 1
        stock_op = orderpoint_form.save()

        orderpoint_form = Form(self.env['stock.warehouse.orderpoint'])
        orderpoint_form.warehouse_id = warehouse
        orderpoint_form.location_id = sub_location
        orderpoint_form.product_id = self.product_01
        orderpoint_form.product_min_qty = 2
        orderpoint_form.product_max_qty = 2
        sub_op = orderpoint_form.save()

        stock_op.action_replenish()
        sub_op.action_replenish()

        po = self.env['purchase.order'].search([('partner_id', '=', self.partner.id)])
        self.assertRecordValues(po.order_line, [
            {'product_id': self.product_01.id, 'product_qty': 1.0, 'orderpoint_id': stock_op.id},
            {'product_id': self.product_01.id, 'product_qty': 2.0, 'orderpoint_id': sub_op.id},
        ])

        po.button_confirm()
        picking = po.picking_ids
        picking.button_validate()

        self.assertRecordValues(picking.move_line_ids, [
            {'product_id': self.product_01.id, 'quantity': 1.0, 'state': 'done', 'location_dest_id': stock_location.id},
            {'product_id': self.product_01.id, 'quantity': 2.0, 'state': 'done', 'location_dest_id': sub_location.id},
        ])

    def test_2steps_and_partner_on_orderpoint(self):
        """
        Suppose a 2-steps receipt
        This test ensures that an orderpoint with its route and supplied defined correctly works
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)])
        route_buy_id = self.ref('purchase_stock.route_warehouse0_buy')

        warehouse.reception_steps = 'two_steps'

        orderpoint = self.env['stock.warehouse.orderpoint'].create({
            'name': 'RR for %s' % self.product_01.name,
            'warehouse_id': warehouse.id,
            'location_id': warehouse.lot_stock_id.id,
            'trigger': 'manual',
            'product_id': self.product_01.id,
            'product_min_qty': 1,
            'product_max_qty': 5,
            'route_id': route_buy_id,
            'supplier_id': self.product_01.seller_ids.id,
        })
        orderpoint.action_replenish()

        po_line = self.env['purchase.order.line'].search([('partner_id', '=', self.partner.id), ('product_id', '=', self.product_01.id)])
        self.assertEqual(po_line.product_qty, 5)

    def test_change_of_scheduled_date(self):
        """
        A user creates a delivery, an orderpoint is created. Its forecast
        quantity becomes -1 and the quantity to order is 1. Then the user
        postpones the scheduled date of the delivery. The quantities of the
        orderpoint should be reset to zero.
        """
        delivery_form = Form(self.env['stock.picking'])
        delivery_form.partner_id = self.partner
        delivery_form.picking_type_id = self.env.ref('stock.picking_type_out')
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product_01
            move.product_uom_qty = 1
        delivery = delivery_form.save()
        delivery.action_confirm()

        delivery.move_ids.flush_recordset()
        self.env['stock.warehouse.orderpoint']._get_orderpoint_action()

        orderpoint = self.env['stock.warehouse.orderpoint'].search([('product_id', '=', self.product_01.id)])
        self.assertRecordValues(orderpoint, [
            {'qty_forecast': -1, 'qty_to_order': 1},
        ])

        # invalidate the fields that will eventually be inconsistent
        orderpoint.invalidate_model(fnames=['qty_forecast', 'qty_to_order'])
        orderpoint.product_id.invalidate_model(fnames=['virtual_available'])

        delivery.scheduled_date += td(days=7)
        self.assertRecordValues(orderpoint, [
            {'qty_forecast': 0, 'qty_to_order': 0},
        ])

    def test_decrease_qty_multi_step_receipt(self):
        """
        Two-steps receipt. An orderpoint generates a move from Input to Stock
        with 5 x Product01 and a purchase order to fulfill the need of that SM.
        Then, the user decreases the qty on the PO and confirms it. The existing
        SM should be updated and another one should be created (from Vendors to
        Input, for the PO)
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.reception_steps = 'two_steps'
        input_location_id = warehouse.wh_input_stock_loc_id.id
        stock_location_id = warehouse.lot_stock_id.id
        customer_location_id = self.ref('stock.stock_location_customers')
        supplier_location_id = self.ref('stock.stock_location_suppliers')

        self.product_01.description = 'Super Note'

        op = self.env['stock.warehouse.orderpoint'].create({
            'name': self.product_01.name,
            'location_id': stock_location_id,
            'product_id': self.product_01.id,
            'product_min_qty': 0,
            'product_max_qty': 0,
            'trigger': 'manual',
        })

        out_move = self.env['stock.move'].create({
            'name': self.product_01.name,
            'product_id': self.product_01.id,
            'product_uom': self.product_01.uom_id.id,
            'product_uom_qty': 5,
            'location_id': stock_location_id,
            'location_dest_id': customer_location_id,
        })
        out_move._action_confirm()

        op.action_replenish()

        moves = self.env['stock.move'].search([('id', '!=', out_move.id), ('product_id', '=', self.product_01.id)])
        self.assertRecordValues(moves, [
            {'location_id': input_location_id, 'location_dest_id': stock_location_id, 'product_uom_qty': 5}
        ])

        purchase = self.env['purchase.order'].search([('partner_id', '=', self.partner.id)], order="id desc", limit=1)
        with Form(purchase) as form:
            with form.order_line.edit(0) as line:
                line.product_qty = 4
        purchase.button_confirm()

        moves = self.env['stock.move'].search([('id', '!=', out_move.id), ('product_id', '=', self.product_01.id)], order='id desc')
        self.assertRecordValues(moves, [
            {'location_id': supplier_location_id, 'location_dest_id': input_location_id, 'product_qty': 4},
            {'location_id': input_location_id, 'location_dest_id': stock_location_id, 'product_qty': 4},
        ])

    def test_decrease_qty_multi_step_receipt02(self):
        """
        Two-steps receipt. An orderpoint generates a move from Input to Stock
        with 4 x Product01 and a purchase order to fulfill the need of that SM.
        Then, the user increases and decreases the qty on the PO. The existing
        SMs should be updated.
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.reception_steps = 'two_steps'
        input_location_id = warehouse.wh_input_stock_loc_id.id
        stock_location_id = warehouse.lot_stock_id.id
        supplier_location_id = self.ref('stock.stock_location_suppliers')

        self.product_01.description = False

        op = self.env['stock.warehouse.orderpoint'].create({
            'name': self.product_01.name,
            'location_id': stock_location_id,
            'product_id': self.product_01.id,
            'product_min_qty': 4,
            'product_max_qty': 4,
            'trigger': 'manual',
        })
        op.action_replenish()

        purchase = self.env['purchase.order'].search([('partner_id', '=', self.partner.id)], order="id desc", limit=1)
        with Form(purchase) as form:
            with form.order_line.edit(0) as line:
                line.product_qty = 10
        purchase.button_confirm()

        moves = self.env['stock.move'].search([('product_id', '=', self.product_01.id)], order='id desc')
        self.assertRecordValues(moves, [
            {'location_id': input_location_id, 'location_dest_id': stock_location_id, 'product_qty': 6},
            {'location_id': supplier_location_id, 'location_dest_id': input_location_id, 'product_qty': 10},
            {'location_id': input_location_id, 'location_dest_id': stock_location_id, 'product_qty': 4},
        ])

        with Form(purchase) as form:
            with form.order_line.edit(0) as line:
                line.product_qty = 1

        moves = self.env['stock.move'].search([('product_id', '=', self.product_01.id)], order='id desc')
        self.assertRecordValues(moves, [
            {'location_id': supplier_location_id, 'location_dest_id': input_location_id, 'product_qty': 1},
            {'location_id': input_location_id, 'location_dest_id': stock_location_id, 'product_qty': 1},
        ])

    def test_add_line_to_existing_draft_po(self):
        """
        Days to purchase = 10
        Two products P1, P2 from the same supplier
        Several use cases, each time we run the RR one by one. Then, according
        to the dates and the configuration, it should use the existing PO or not
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)

        self.env.company.days_to_purchase = 10
        expected_order_date = dt.combine(dt.today() + td(days=10), time(12))
        expected_delivery_date = expected_order_date + td(days=1.0)

        product_02 = self.env['product.product'].create({
            'name': 'Super Product',
            'type': 'product',
            'seller_ids': [(0, 0, {'partner_id': self.partner.id})],
        })

        op_01, op_02 = self.env['stock.warehouse.orderpoint'].create([{
            'warehouse_id': warehouse.id,
            'location_id': warehouse.lot_stock_id.id,
            'product_id': p.id,
            'product_min_qty': 1,
            'product_max_qty': 0,
        } for p in [self.product_01, product_02]])

        op_01.action_replenish()
        po01 = self.env['purchase.order'].search([], order='id desc', limit=1)
        self.assertEqual(po01.date_order, expected_order_date)

        op_02.action_replenish()
        self.assertEqual(po01.date_order, expected_order_date)
        self.assertRecordValues(po01.order_line, [
            {'product_id': self.product_01.id, 'date_planned': expected_delivery_date},
            {'product_id': product_02.id, 'date_planned': expected_delivery_date},
        ])

        # Reset and try another flow
        po01.button_cancel()
        op_01.action_replenish()
        po02 = self.env['purchase.order'].search([], order='id desc', limit=1)
        self.assertNotEqual(po02, po01)

        with freeze_time(dt.today() + td(days=1)):
            op_02.invalidate_recordset(fnames=['lead_days_date'])
            op_02.action_replenish()
            self.assertEqual(po02.date_order, expected_order_date)
            self.assertRecordValues(po02.order_line, [
                {'product_id': self.product_01.id, 'date_planned': expected_delivery_date},
                {'product_id': product_02.id, 'date_planned': expected_delivery_date + td(days=1)},
            ])

        # Restrict the merge with POs that have their order deadline in [today - 2 days, today + 2 days]
        self.env['ir.config_parameter'].set_param('purchase_stock.delta_days_merge', '2')

        # Reset and try with a second RR executed in the dates range (-> should still use the existing PO)
        po02.button_cancel()
        op_01.action_replenish()
        po03 = self.env['purchase.order'].search([], order='id desc', limit=1)
        self.assertNotEqual(po03, po02)

        with freeze_time(dt.today() + td(days=2)):
            op_02.invalidate_recordset(fnames=['lead_days_date'])
            op_02.action_replenish()
            self.assertEqual(po03.date_order, expected_order_date)
            self.assertRecordValues(po03.order_line, [
                {'product_id': self.product_01.id, 'date_planned': expected_delivery_date},
                {'product_id': product_02.id, 'date_planned': expected_delivery_date + td(days=2)},
            ])

        # Reset and try with a second RR executed after the dates range (-> should not use the existing PO)
        po03.button_cancel()
        op_01.action_replenish()
        po04 = self.env['purchase.order'].search([], order='id desc', limit=1)
        self.assertNotEqual(po04, po03)

        with freeze_time(dt.today() + td(days=3)):
            op_02.invalidate_recordset(fnames=['lead_days_date'])
            op_02.action_replenish()
            self.assertEqual(po04.order_line.product_id, self.product_01, 'There should be only a line for product 01')
            po05 = self.env['purchase.order'].search([], order='id desc', limit=1)
            self.assertNotEqual(po05, po04, 'A new PO should be generated')
            self.assertEqual(po05.order_line.product_id, product_02)

    def test_update_po_line_without_purchase_access_right(self):
        """ Test that a user without purchase access right can update a PO line from picking."""
        # create a user with only inventory access right
        user = self.env['res.users'].create({
            'name': 'Inventory Manager',
            'login': 'inv_manager',
            'groups_id': [(6, 0, [self.env.ref('stock.group_stock_user').id])]
        })
        product = self.env['product.product'].create({
            'name': 'Storable Product',
            'type': 'product',
            'seller_ids': [(0, 0, {'partner_id': self.partner.id})],
        })
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        self.env['stock.warehouse.orderpoint'].create({
            'warehouse_id': warehouse.id,
            'location_id': warehouse.lot_stock_id.id,
            'product_id': product.id,
            'product_min_qty': 5,
            'product_max_qty': 0,
        })
        # run the scheduler
        self.env['procurement.group'].run_scheduler()
        # check that the PO line is created
        po_line = self.env['purchase.order.line'].search([('product_id', '=', product.id)])
        self.assertEqual(len(po_line), 1, 'There should be only one PO line')
        self.assertEqual(po_line.product_qty, 5, 'The PO line quantity should be 5')
        # Update the po line from the picking
        picking = self.env['stock.picking'].with_user(user).create({
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'picking_type_id': warehouse.out_type_id.id,
            'move_ids': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_uom': product.uom_id.id,
                'product_uom_qty': 1,
                'location_id': warehouse.lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            })],
            'state': 'draft',
        })
        picking.with_user(user).action_assign()
        # check that the PO line quantity has been updated
        self.assertEqual(po_line.product_qty, 6, 'The PO line quantity should be 6')
