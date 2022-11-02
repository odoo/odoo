# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests.common import Form
from odoo.tools.float_utils import float_round, float_compare

from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon
from odoo.addons.mrp_account.tests.test_bom_price import TestBomPriceCommon

class TestAccountSubcontractingFlows(TestMrpSubcontractingCommon):
    def test_subcontracting_account_flow_1(self):
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.uom_unit = self.env.ref('uom.product_uom_unit')
        self.env.ref('product.product_category_all').property_cost_method = 'fifo'

        # IN 10@10 comp1 10@20 comp2
        move1 = self.env['stock.move'].create({
            'name': 'IN 10 units @ 10.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.env.company.subcontracting_location_id.id,
            'product_id': self.comp1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10.0
        move1._action_done()
        move2 = self.env['stock.move'].create({
            'name': 'IN 10 units @ 20.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.env.company.subcontracting_location_id.id,
            'product_id': self.comp2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 20.0,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 10.0
        move2._action_done()

        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 1
        picking_receipt = picking_form.save()
        picking_receipt.move_ids.price_unit = 15.0

        picking_receipt.action_confirm()
        # Suppose the additional cost changes:
        picking_receipt.move_ids.price_unit = 30.0
        picking_receipt.move_ids.quantity_done = 1.0
        picking_receipt._action_done()

        mo = picking_receipt._get_subcontract_production()
        # Finished is made of 1 comp1 and 1 comp2.
        # Cost of comp1 = 10
        # Cost of comp2 = 20
        # --> Cost of finished = 10 + 20 = 30
        # Additionnal cost = 30 (from the purchase order line or directly set on the stock move here)
        # Total cost of subcontracting 1 unit of finished = 30 + 30 = 60
        self.assertEqual(mo.move_finished_ids.stock_valuation_layer_ids.value, 60)
        self.assertEqual(picking_receipt.move_ids.stock_valuation_layer_ids.value, 0)
        self.assertEqual(picking_receipt.move_ids.product_id.value_svl, 60)

        # Do the same without any additionnal cost
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 1
        picking_receipt = picking_form.save()
        picking_receipt.move_ids.price_unit = 0

        picking_receipt.action_confirm()
        picking_receipt.move_ids.quantity_done = 1.0
        picking_receipt._action_done()

        mo = picking_receipt._get_subcontract_production()
        # In this case, since there isn't any additionnal cost, the total cost of the subcontracting
        # is the sum of the components' costs: 10 + 20 = 30
        self.assertEqual(mo.move_finished_ids.stock_valuation_layer_ids.value, 30)
        self.assertEqual(picking_receipt.move_ids.product_id.value_svl, 90)

    def test_subcontracting_account_backorder(self):
        """ This test uses tracked (serial and lot) component and tracked (serial) finished product
        The original subcontracting production order will be split into 4 backorders. This test
        ensure the extra cost asked from the subcontractor is added correctly on all the finished
        product valuation layer. Not only the first one. """
        todo_nb = 4
        self.comp2.tracking = 'lot'
        self.comp1.tracking = 'serial'
        self.comp2.standard_price = 100
        self.finished.tracking = 'serial'
        self.env.ref('product.product_category_all').property_cost_method = 'fifo'

        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = todo_nb
        picking_receipt = picking_form.save()
        # Mimic the extra cost on the po line
        picking_receipt.move_ids.price_unit = 50
        picking_receipt.action_confirm()

        # We should be able to call the 'record_components' button
        self.assertTrue(picking_receipt.display_action_record_components)

        lot_comp2 = self.env['stock.lot'].create({
            'name': 'lot_comp2',
            'product_id': self.comp2.id,
            'company_id': self.env.company.id,
        })
        serials_finished = []
        serials_comp1 = []
        for i in range(todo_nb):
            serials_finished.append(self.env['stock.lot'].create({
                'name': 'serial_fin_%s' % i,
                'product_id': self.finished.id,
                'company_id': self.env.company.id,
            }))
            serials_comp1.append(self.env['stock.lot'].create({
                'name': 'serials_comp1_%s' % i,
                'product_id': self.comp1.id,
                'company_id': self.env.company.id,
            }))

        for i in range(todo_nb):
            action = picking_receipt.action_record_components()
            mo = self.env['mrp.production'].browse(action['res_id'])
            mo_form = Form(mo.with_context(**action['context']), view=action['view_id'])
            mo_form.lot_producing_id = serials_finished[i]
            with mo_form.move_line_raw_ids.edit(0) as ml:
                self.assertEqual(ml.product_id, self.comp1)
                ml.lot_id = serials_comp1[i]
            with mo_form.move_line_raw_ids.edit(1) as ml:
                self.assertEqual(ml.product_id, self.comp2)
                ml.lot_id = lot_comp2
            mo = mo_form.save()
            mo.subcontracting_record_component()

        # We should not be able to call the 'record_components' button

        picking_receipt.button_validate()

        f_layers = self.finished.stock_valuation_layer_ids
        self.assertEqual(len(f_layers), 4)
        for layer in f_layers:
            self.assertEqual(layer.value, 100 + 50)

    def test_tracked_compo_and_backorder(self):
        """
        Suppose a subcontracted product P with two tracked components, P is FIFO
        Create a receipt for 10 x P, receive 5, then 3 and then 2
        """
        self.env.ref('product.product_category_all').property_cost_method = 'fifo'
        self.comp1.tracking = 'lot'
        self.comp1.standard_price = 10
        self.comp2.tracking = 'lot'
        self.comp2.standard_price = 20

        lot01, lot02 = self.env['stock.lot'].create([{
            'name': "Lot of %s" % product.name,
            'product_id': product.id,
            'company_id': self.env.company.id,
        } for product in (self.comp1, self.comp2)])

        receipt_form = Form(self.env['stock.picking'])
        receipt_form.picking_type_id = self.env.ref('stock.picking_type_in')
        receipt_form.partner_id = self.subcontractor_partner1
        with receipt_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 10
        receipt = receipt_form.save()
        # add an extra cost
        receipt.move_ids.price_unit = 50
        receipt.action_confirm()

        for qty_producing in (5, 3, 2):
            action = receipt.action_record_components()
            mo = self.env['mrp.production'].browse(action['res_id'])
            mo_form = Form(mo.with_context(**action['context']), view=action['view_id'])
            mo_form.qty_producing = qty_producing
            with mo_form.move_line_raw_ids.edit(0) as ml:
                ml.lot_id = lot01
            with mo_form.move_line_raw_ids.edit(1) as ml:
                ml.lot_id = lot02
            mo = mo_form.save()
            mo.subcontracting_record_component()

            action = receipt.button_validate()
            if isinstance(action, dict):
                wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
                wizard.process()
                receipt = receipt.backorder_ids

        self.assertRecordValues(self.finished.stock_valuation_layer_ids, [
            {'quantity': 5, 'value': 5 * (10 + 20 + 50)},
            {'quantity': 3, 'value': 3 * (10 + 20 + 50)},
            {'quantity': 2, 'value': 2 * (10 + 20 + 50)},
        ])


class TestBomPriceSubcontracting(TestBomPriceCommon):

    def test_01_compute_price_subcontracting_cost(self):
        """Test calculation of bom cost with subcontracting."""
        self.table_head.uom_po_id = self.dozen
        partner = self.env['res.partner'].create({
            'name': 'A name can be a Many2one...'
        })
        (self.bom_1 | self.bom_2).write({
            'type': 'subcontract',
            'subcontractor_ids': [Command.link(partner.id)]
        })
        suppliers = self.env['product.supplierinfo'].create([
            {
                'partner_id': partner.id,
                'product_tmpl_id': self.dining_table.product_tmpl_id.id,
                'price': 150.0,
            }, {
                'partner_id': partner.id,
                'product_tmpl_id': self.table_head.product_tmpl_id.id,
                'price': 120.0,  # 10 by Unit because uom_po_id is in dozen
            }
        ])
        self.assertEqual(suppliers.mapped('is_subcontractor'), [True, True])

        # -----------------------------------------------------------------
        # Cost of BoM (Dining Table 1 Unit)
        # -----------------------------------------------------------------
        # Component Cost =  Table Head     1 Unit * 300 = 300 (478.75 from it's components)
        #                   Screw          5 Unit *  10 =  50
        #                   Leg            4 Unit *  25 = 100
        #                   Glass          1 Unit * 100 = 100
        #                   Subcontracting 1 Unit * 150 = 150
        # Total = 700 [878.75 if components of Table Head considered] (for 1 Unit)
        # -----------------------------------------------------------------
        self.assertEqual(self.dining_table.standard_price, 1000, "Initial price of the Product should be 1000")
        self.dining_table.button_bom_cost()
        self.assertEqual(float_round(self.dining_table.standard_price, precision_digits=2), 700.0, "After computing price from BoM price should be 700")

        # Cost of BoM (Table Head 1 Dozen)
        # -----------------------------------------------------------------
        # Component Cost =  Plywood Sheet   12 Unit * 200 = 2400
        #                   Bolt            60 Unit *  10 =  600
        #                   Colour          12 Unit * 100 = 1200
        #                   Corner Slide    57 Unit * 25  = 1425
        #                   Subcontracting  1 Dozen * 120 =  120
        #                                           Total = 5745
        #                          1 Unit price (5745/12) =  478.75
        # -----------------------------------------------------------------

        self.assertEqual(self.table_head.standard_price, 300, "Initial price of the Product should be 300")
        self.Product.browse([self.dining_table.id, self.table_head.id]).action_bom_cost()
        self.assertEqual(float_compare(self.table_head.standard_price, 478.75, precision_digits=2), 0, "After computing price from BoM price should be 878.75")
        self.assertEqual(float_compare(self.dining_table.standard_price, 878.75, precision_digits=2), 0, "After computing price from BoM price should be 878.75")
