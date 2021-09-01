# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime as dt
from datetime import timedelta as td

from odoo import SUPERUSER_ID
from odoo.tests import Form
from odoo.tests.common import SavepointCase
from odoo.exceptions import UserError


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
        product_form.description = 'Internal Notes'
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
        warehouse_2 = self.env['stock.warehouse'].create({'name': 'WH 2', 'code': 'WH2', 'company_id': self.env.company.id, 'partner_id': self.env.company.partner_id.id, 'reception_steps': 'one_step'})
        
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
        
        # Check the picking type on the purchase order
        purchase_order.picking_type_id = warehouse_2.in_type_id
        with self.assertRaises(UserError):
            purchase_order.button_confirm()
        purchase_order.picking_type_id = warehouse_1.in_type_id

        # On the po generated, the source document should be the name of the reordering rule
        self.assertEqual(order_point.name, purchase_order.origin, 'Source document on purchase order should be the name of the reordering rule.')
        self.assertEqual(purchase_order.order_line.product_qty, 10)
        self.assertEqual(purchase_order.order_line.name, 'Product A')

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
        product_form.type = 'product'
        with product_form.seller_ids.new() as s:
            s.name = partner
        product = product_form.save()

        product_form = Form(self.env['product.product'])
        product_form.name = 'Product BUY + MTO'
        product_form.type = 'product'
        product_form.route_ids.add(route_buy)
        product_form.route_ids.add(route_mto)
        with product_form.seller_ids.new() as s:
            s.name = partner
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
        customer_picking.move_lines.filtered(lambda m: m.product_id == product_buy_mto).procure_method = 'make_to_order'
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
        customer_picking.move_lines.filtered(lambda m: m.product_id == product_buy_mto).procure_method = 'make_to_order'
        customer_picking.action_confirm()
        self.env['stock.warehouse.orderpoint'].flush()

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
        product_form.type = 'product'
        with product_form.seller_ids.new() as s:
            s.name = partner
        product = product_form.save()

        product_form = Form(self.env['product.product'])
        product_form.name = 'Product BUY + MTO'
        product_form.type = 'product'
        product_form.route_ids.add(route_buy)
        product_form.route_ids.add(route_mto)
        with product_form.seller_ids.new() as s:
            s.name = partner
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
        customer_picking.move_lines.filtered(lambda m: m.product_id == product_buy_mto).procure_method = 'make_to_order'
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

        self.env['stock.warehouse.orderpoint'].flush()
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
        customer_picking.move_lines.filtered(lambda m: m.product_id == product_buy_mto).procure_method = 'make_to_order'
        customer_picking.action_confirm()
        self.env['stock.warehouse.orderpoint'].flush()

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
             ('location_id', '=', customer_loc.id)
            ]
        )
        route_mto = self.env["stock.location.route"].create({
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
        self.env['ir.translation']._set_ids('product.template,name', 'model', 'fr_FR', product.product_tmpl_id.ids, 'produit en français')
        self.env['ir.translation']._set_ids('product.product,name', 'model', 'fr_FR', product.ids, 'produit en français')
        default_vendor = self.env["res.partner"].create({
            "name": "Supplier A",
        })
        self.env["product.supplierinfo"].create({
            "name": default_vendor.id,
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
        self.env.cache.invalidate()

        self.env["procurement.group"].run([procurement])

        po_line = self.env["purchase.order.line"].search(
            [("product_id", "=", product.id)])
        self.assertTrue(po_line)
        self.assertEqual("[A] product TEST", po_line.name)
