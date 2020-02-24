# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime as dt
from datetime import timedelta as td

from odoo.tests import Form
from odoo.tests.common import SavepointCase


class TestReorderingRule(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestReorderingRule, cls).setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Smith'
        })

        # create product and set the vendor
        product_form = Form(cls.env['product.product'])
        product_form.name = 'Product A'
        product_form.type = 'product'
        with product_form.seller_ids.new() as seller:
            seller.name = cls.partner
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

        # picking confirm
        customer_picking.action_confirm()

        # Run scheduler
        self.env['procurement.group'].run_scheduler()

        # Check purchase order created or not
        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.partner.id)])
        self.assertTrue(purchase_order, 'No purchase order created.')

        # On the po generated, the source document should be the name of the reordering rule
        self.assertEqual(order_point.name, purchase_order.origin, 'Source document on purchase order should be the name of the reordering rule.')
        self.assertEqual(purchase_order.order_line.product_qty, 10)

        # Increase the quantity on the RFQ before confirming it
        purchase_order.order_line.product_qty = 12
        purchase_order.button_confirm()

        self.assertEqual(purchase_order.picking_ids.move_lines.filtered(lambda m: m.product_id == self.product_01).product_qty, 12)
        next_picking = purchase_order.picking_ids.move_lines.move_dest_ids.picking_id
        self.assertEqual(len(next_picking), 2)
        self.assertEqual(next_picking[0].move_lines.filtered(lambda m: m.product_id == self.product_01).product_qty, 10)
        self.assertEqual(next_picking[1].move_lines.filtered(lambda m: m.product_id == self.product_01).product_qty, 2)

        # Increase the quantity on the PO
        purchase_order.order_line.product_qty = 15
        self.assertEqual(purchase_order.picking_ids.move_lines.product_qty, 15)
        self.assertEqual(next_picking[0].move_lines.filtered(lambda m: m.product_id == self.product_01).product_qty, 10)
        self.assertEqual(next_picking[1].move_lines.filtered(lambda m: m.product_id == self.product_01).product_qty, 5)

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
        customer_picking.move_lines[0].location_id = subloc_1.id
        customer_picking.move_lines[1].location_id = subloc_2.id

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

        self.assertEqual(purchase_order.picking_ids.move_lines[-1].product_qty, 5)
        self.assertEqual(purchase_order.picking_ids.move_lines[-1].location_dest_id, warehouse_1.lot_stock_id)

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
            "name": default_vendor.id,
            "product_tmpl_id": product.product_tmpl_id.id,
            "delay": 7,
        })
        self.env["product.supplierinfo"].create({
            "name": secondary_vendor.id,
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
                    "supplier_id": secondary_vendor,
                }
            )])
        po_line = self.env["purchase.order.line"].search(
            [("product_id", "=", product.id)])
        self.assertTrue(po_line)
        self.assertEqual(po_line.partner_id, secondary_vendor)
