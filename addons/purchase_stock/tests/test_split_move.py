# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestPurchase


class TestSplitMove(TestPurchase):

    def test_split_mto_mts_po(self):
        """ Purchase Order of Product in MTO:
        - Create a Picking Out for 10 units.
        - On the RFQ, change quantity from 10 to 5 and validate and receive products.
        - On the Picking Out, split the stock move into two, one of 5 in MTO, one of 5 in MTS.
        - Update quants and products should be reserved in the Picking, then mark as done.
        This test ensure that when initial demand is decreased, the initial demand in destination move should be splitted into two -> one in        MTO and one in MTS.
        """

        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.cust_location = self.env.ref('stock.stock_location_customers')
        # Create a Picking Out for Product A with quantity = 10
        picking_out = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.cust_location.id,
            'partner_id': self.partner_1.id,
            'picking_type_id': self.ref('stock.picking_type_out'),
        })
        move1 = self.env['stock.move'].create({
            'name': self.product_1.name,
            'product_id': self.product_1.id,
            'product_uom_qty': 10,
            'product_uom': self.product_1.uom_id.id,
            'picking_id': picking_out.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.cust_location.id,
            'procure_method': 'make_to_order',
        })
        move1._action_confirm()

        # Find the RFQ created through Picking Out.
        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.partner_1.id)])
        self.assertTrue(purchase_order, 'No purchase order created.')

        # Check purchase order line data.
        purchase_order_line = purchase_order.order_line

        # ----------------------------------------------------------------------
        # Decrease the Initial demand
        # ----------------------------------------------------------------------
        #   Product A ( 10 Unit ) --> Product A ( 5 Unit )
        # ----------------------------------------------------------------------
        for line in purchase_order_line:
            self.assertEqual(line.product_uom_qty, 10.0, 'Wrong product quantity.')
            line.write({'product_qty': 5.0})
            line._onchange_quantity()
            self.assertEqual(line.product_uom_qty, 5.0, 'Wrong product quantity.')
        # Confirm the Purchase Order
        purchase_order.button_confirm()

        # Picking In should be created
        picking_in = purchase_order.picking_ids
        self.assertTrue(picking_in, 'Picking should be created')
        # Destination move of move in Picking In should be move in Picking OUT.
        self.assertEqual(picking_in.move_lines.move_dest_ids, move1, 'Wrong move in destination moves.')
        picking_in.action_confirm()
        picking_in.action_assign()
        # Recieve products
        for line in picking_in.move_lines:
            line.write({'quantity_done': 5.0})
        # Complete the PO.
        picking_in.action_done()
        self.assertEqual(picking_in.state, 'done', 'Picking should be in done state.')
        self.assertEqual(purchase_order.state, 'purchase', 'Wrong state of Purchase order.')

        # ======================================================================
        # Before splitting move:
        # ----------------------
        #   Product A ( 10 Unit ) - MTO
        #
        # After splitting move:
        # ---------------------
        #   Product A (  5 unit ) - MTO
        #   ---------------------------
        #   Product A (  5 unit ) - MTS
        # ======================================================================

        # Check that new line of MTS is created for remaining product in Picking Out and it should be MTS.
        self.assertEqual(len(picking_out.move_lines), 2, 'New move line of MTS must be created.')
        self.assertEqual(picking_out.move_lines[1].procure_method, 'make_to_stock', 'New move line must be - Make to Stock.')
        self.assertEqual(picking_out.move_lines[1].product_uom_qty, 5.0, 'Wrong product quantity.')

        # Update quants and Validate the Picking OUT.
        self.env['stock.quant']._update_available_quantity(self.product_1, self.stock_location, 5.0)
        picking_out.action_assign()
        self.assertEqual(picking_out.state, 'assigned', 'products must be assigned to the picking.')

        res_dict_2 = picking_out.button_validate()
        wizard_2 = self.env[(res_dict_2.get('res_model'))].browse(res_dict_2.get('res_id'))
        wizard_2.process()
        self.assertEqual(picking_out.state, 'done', 'Picking should be in done state.')
