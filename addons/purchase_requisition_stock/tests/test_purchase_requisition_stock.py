# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.purchase_requisition.tests.common import TestPurchaseRequisitionCommon
from odoo.tests import Form
from odoo import Command


class TestPurchaseRequisitionStock(TestPurchaseRequisitionCommon):

    def test_02_purchase_requisition_stock(self):
        """Plays with the sequence of regular supplier infos and one created by blanket orders."""
        # Product creation
        unit = self.ref("uom.product_uom_unit")
        warehouse1 = self.env.ref('stock.warehouse0')
        route_buy = self.ref('purchase_stock.route_warehouse0_buy')
        route_mto = warehouse1.mto_pull_id.route_id.id
        vendor1 = self.env['res.partner'].create({'name': 'AAA', 'email': 'from.test@example.com'})
        vendor2 = self.env['res.partner'].create({'name': 'BBB', 'email': 'from.test2@example.com'})
        supplier_info1 = self.env['product.supplierinfo'].create({
            'partner_id': vendor1.id,
            'price': 50,
        })
        product_test = self.env['product.product'].create({
            'name': 'Usb Keyboard',
            'type': 'product',
            'uom_id': unit,
            'uom_po_id': unit,
            'seller_ids': [(6, 0, [supplier_info1.id])],
            'route_ids': [(6, 0, [route_buy, route_mto])]
        })

        # Stock picking
        stock_location = self.env.ref('stock.stock_location_stock')
        customer_location = self.env.ref('stock.stock_location_customers')
        move1 = self.env['stock.move'].create({
            'name': '10 in',
            'procure_method': 'make_to_order',
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'product_id': product_test.id,
            'product_uom': unit,
            'product_uom_qty': 10.0,
            'price_unit': 10,
        })
        move1._action_confirm()

        # Verification : there should be a purchase order created with the good price
        purchase1 = self.env['purchase.order'].search([('partner_id', '=', vendor1.id)])
        self.assertEqual(purchase1.order_line.price_unit, 50, 'The price on the purchase order is not the supplierinfo one')

        # Blanket order creation
        line1 = (0, 0, {'product_id': product_test.id, 'product_qty': 18, 'product_uom_id': product_test.uom_po_id.id, 'price_unit': 50})
        requisition_type = self.env['purchase.requisition.type'].create({
            'name': 'Blanket test',
            'quantity_copy': 'none',
        })
        requisition_blanket = self.env['purchase.requisition'].create({
            'line_ids': [line1],
            'type_id': requisition_type.id,
            'vendor_id': vendor2.id,
            'currency_id': self.env.user.company_id.currency_id.id,
        })
        requisition_blanket.action_in_progress()

        # Second stock move
        move2 = self.env['stock.move'].create({
            'name': '10 in',
            'procure_method': 'make_to_order',
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'product_id': product_test.id,
            'product_uom': unit,
            'product_uom_qty': 10.0,
            'price_unit': 10
        })
        move2._action_confirm()

        # As the supplier.info linked to the blanket order has the same price, the first one is stille used.
        self.assertEqual(purchase1.order_line.product_qty, 20)

        # Update the sequence of the blanket order's supplier info.
        supplier_info1.sequence = 2
        requisition_blanket.line_ids.supplier_info_ids.sequence = 1
        # In [13]: [(x.sequence, x.min_qty, x.price, x.partner_id.name) for x in supplier_info1 + requisition_blanket.line_ids.supplier_info_ids]
        # Out[13]: [(2, 0.0, 50.0, 'AAA'), (1, 0.0, 50.0, 'BBB')]

        # Second stock move
        move3 = self.env['stock.move'].create({
            'name': '10 in',
            'procure_method': 'make_to_order',
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'product_id': product_test.id,
            'product_uom': unit,
            'product_uom_qty': 10.0,
            'price_unit': 10
        })
        move3._action_confirm()

        # Verifications
        purchase2 = self.env['purchase.order'].search([('partner_id', '=', vendor2.id), ('requisition_id', '=', requisition_blanket.id)])
        self.assertEqual(len(purchase2), 1)
        self.assertEqual(purchase2.order_line.price_unit, 50, 'The price on the purchase order is not the blanquet order one')

    def test_03_purchase_requisition_stock(self):
        """ Two blanket orders on different 'make to order' products must generate
        two different purchase orders
        """

        # Product creation
        unit = self.ref("uom.product_uom_unit")
        warehouse1 = self.env.ref('stock.warehouse0')
        route_buy = self.ref('purchase_stock.route_warehouse0_buy')
        route_mto = warehouse1.mto_pull_id.route_id.id
        vendor1 = self.env['res.partner'].create({'name': 'AAA', 'email': 'from.test@example.com'})
        supplier_info1 = self.env['product.supplierinfo'].create({
            'partner_id': vendor1.id,
            'price': 50,
        })
        product_1 = self.env['product.product'].create({
            'name': 'product1',
            'type': 'product',
            'uom_id': unit,
            'uom_po_id': unit,
            'seller_ids': [(6, 0, [supplier_info1.id])],
            'route_ids': [(6, 0, [route_buy, route_mto])]
        })
        product_2 = self.env['product.product'].create({
            'name': 'product2',
            'type': 'product',
            'uom_id': unit,
            'uom_po_id': unit,
            'seller_ids': [(6, 0, [supplier_info1.id])],
            'route_ids': [(6, 0, [route_buy, route_mto])]
        })
        # Blanket orders creation
        requisition_type = self.env['purchase.requisition.type'].create({
            'name': 'Blanket test',
            'quantity_copy': 'none',
        })
        line1 = (0, 0, {'product_id': product_1.id, 'product_qty': 18, 'product_uom_id': product_1.uom_po_id.id, 'price_unit': 41})
        line2 = (0, 0, {'product_id': product_2.id, 'product_qty': 18, 'product_uom_id': product_2.uom_po_id.id, 'price_unit': 42})
        requisition_1 = self.env['purchase.requisition'].create({
            'line_ids': [line1],
            'type_id': requisition_type.id,
            'vendor_id': vendor1.id,
            'currency_id': self.env.user.company_id.currency_id.id,
        })
        requisition_2 = self.env['purchase.requisition'].create({
            'line_ids': [line2],
            'type_id': requisition_type.id,
            'vendor_id': vendor1.id,
            'currency_id': self.env.user.company_id.currency_id.id,
        })
        requisition_1.action_in_progress()
        requisition_2.action_in_progress()
        # Stock moves
        stock_location = self.env.ref('stock.stock_location_stock')
        customer_location = self.env.ref('stock.stock_location_customers')
        move1 = self.env['stock.move'].create({
            'name': '10 in',
            'procure_method': 'make_to_order',
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'product_id': product_1.id,
            'product_uom': unit,
            'product_uom_qty': 10.0,
            'price_unit': 100,
        })
        move2 = self.env['stock.move'].create({
            'name': '10 in',
            'procure_method': 'make_to_order',
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'product_id': product_2.id,
            'product_uom': unit,
            'product_uom_qty': 10.0,
            'price_unit': 100,
        })
        move1._action_confirm()
        move2._action_confirm()
        # Verifications
        POL1 = self.env['purchase.order.line'].search([('product_id', '=', product_1.id)]).order_id
        POL2 = self.env['purchase.order.line'].search([('product_id', '=', product_2.id)]).order_id
        self.assertFalse(POL1 == POL2, 'The two blanket orders should generate two purchase different purchase orders')
        POL1.write({'order_line': [
            (0, 0, {
                'name': product_2.name,
                'product_id': product_2.id,
                'product_qty': 5.0,
                'product_uom': product_2.uom_po_id.id,
            })
        ]})
        order_line = self.env['purchase.order.line'].search([
            ('product_id', '=', product_2.id),
            ('product_qty', '=', 5.0),
        ])
        self.assertEqual(order_line.price_unit, 50, 'The supplier info chosen should be the one without requisition id')

    def test_04_purchase_requisition_stock(self):
        """Check that alt PO correctly copies the original PO values"""
        # create original PO
        orig_po = self.env['purchase.order'].create({
            'partner_id': self.res_partner_1.id,
            'picking_type_id': self.env['stock.picking.type'].search([['code', '=', 'outgoing']], limit=1).id,
            'dest_address_id': self.env['res.partner'].create({'name': 'delivery_partner'}).id,
        })
        unit_price = 50
        po_form = Form(orig_po)
        with po_form.order_line.new() as line:
            line.product_id = self.product_09
            line.product_qty = 5.0
            line.price_unit = unit_price
        po_form.save()

        # create an alt PO
        action = orig_po.action_create_alternative()
        alt_po_wiz = Form(self.env['purchase.requisition.create.alternative'].with_context(**action['context']))
        alt_po_wiz.partner_id = self.res_partner_1
        alt_po_wiz.copy_products = True
        alt_po_wiz = alt_po_wiz.save()
        alt_po_wiz.action_create_alternative()

        # check alt PO was created with correct values
        alt_po = orig_po.alternative_po_ids.filtered(lambda po: po.id != orig_po.id)
        self.assertEqual(orig_po.picking_type_id, alt_po.picking_type_id,
                         "Alternative PO should have copied the picking type from original PO")
        self.assertEqual(orig_po.dest_address_id, alt_po.dest_address_id,
                         "Alternative PO should have copied the destination address from original PO")
        self.assertEqual(orig_po.order_line.product_id, alt_po.order_line.product_id,
                         "Alternative PO should have copied the product to purchase from original PO")
        self.assertEqual(orig_po.order_line.product_qty, alt_po.order_line.product_qty,
                         "Alternative PO should have copied the qty to purchase from original PO")
        self.assertEqual(len(alt_po.alternative_po_ids), 2,
                         "Newly created PO should be auto-linked to itself and original PO")

        # confirm the alt PO, original PO should be cancelled
        action = alt_po.button_confirm()
        warning_wiz = Form(
            self.env['purchase.requisition.alternative.warning'].with_context(**action['context']))
        warning_wiz = warning_wiz.save()
        self.assertEqual(len(warning_wiz.alternative_po_ids), 1,
                         "POs not in a RFQ status should not be listed as possible to cancel")
        warning_wiz.action_cancel_alternatives()
        self.assertEqual(orig_po.state, 'cancel', "Original PO should have been cancelled")

    def test_05_move_dest_links_alternatives(self):
        """ Checks if Purchase Order alternatives are correctly linked to the original PO's move_dest_ids. """
        # Prepare test data
        wh = self.env.ref('stock.warehouse0')
        buy_route_id = self.ref('purchase_stock.route_warehouse0_buy')
        vendor_1 = self.env['res.partner'].create({'name': 'Vendor 1'})
        vendor_2 = self.env['res.partner'].create({'name': 'Vendor 2'})
        product = self.env['product.product'].create({
            'name': 'Test product',
            'type': 'product',
            'seller_ids': [Command.create({
                'partner_id': vendor_1.id,
                'price': 10.0,
                'delay': 0,
            })],
            'route_ids': [Command.set([buy_route_id])],
        })

        # Sets the warehouse to do two-steps receptions
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_multi_step_rule = self.env.ref('stock.group_adv_location')
        self.env.user.write({'groups_id': [(3, grp_multi_loc.id)]})
        self.env.user.write({'groups_id': [(3, grp_multi_step_rule.id)]})
        wh.reception_steps = 'two_steps'

        # Create a reordering rule for the product and
        self.env['stock.warehouse.orderpoint'].create({
            'name': 'RR for %s' % product.name,
            'warehouse_id': wh.id,
            'location_id': wh.lot_stock_id.id,
            'product_id': product.id,
            'product_min_qty': 1,
            'product_max_qty': 10,
        })
        # Run scheduler to create internal transfer from Input -> Stock and generate the Purchase Order
        self.env['procurement.group'].run_scheduler()
        # Find the internal move (Input -> Stock) that has been generated
        int_move = self.env['stock.move'].search([('product_id', '=', product.id)])
        self.assertEqual(int_move.quantity, 0, "No product should be available, as no products were received at this point.")
        # Find the Purchase Order generated by the orderpoint
        orig_po = self.env['purchase.order'].search([('partner_id', '=', vendor_1.id)])
        self.assertEqual(len(orig_po.ids), 1, "Only one PO should have been generated.")
        # Create an alternative RFQ for another vendor
        action = orig_po.action_create_alternative()
        alt_po_wizard = Form(self.env['purchase.requisition.create.alternative'].with_context(**action['context']))
        alt_po_wizard.partner_id = vendor_2
        alt_po_wizard.copy_products = True
        alt_po_wizard = alt_po_wizard.save()
        alt_po_wizard.action_create_alternative()
        # Find the alternative Purchase Order
        alt_po = orig_po.alternative_po_ids.filtered(lambda po: po.id != orig_po.id)
        self.assertEqual(len(orig_po.alternative_po_ids), 2, "Base PO should be linked with the alternative PO.")
        # Validate it
        warning_action = alt_po.button_confirm()
        warning_wizard = Form(self.env[warning_action['res_model']].with_context(**warning_action['context']))
        warning_wizard = warning_wizard.save()
        # Cancel other alternatives
        warning_wizard.action_cancel_alternatives()
        self.assertEqual(orig_po.state, 'cancel', "Original PO should have been cancelled.")
        self.assertEqual(alt_po.state, 'purchase', "Alternative PO should have been confirmed.")
        # Set all qty as done and validate the alternative PO's picking
        in_picking = alt_po.picking_ids
        self.assertEqual(in_picking.picking_type_id.code, 'incoming', "Must be the reception picking.")
        in_picking.move_ids.quantity = 10
        in_picking.move_ids.picked = True
        in_picking.button_validate()
        # Quantity should be reserved in the internal transfer's move
        self.assertEqual(int_move.quantity, 10, "Quantity should be reserved in the original internal move.")
        self.assertEqual(int_move.move_orig_ids.id, in_picking.move_ids.id, "Both moves should be correctly chained together.")
