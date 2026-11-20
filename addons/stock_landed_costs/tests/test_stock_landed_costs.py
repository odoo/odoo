# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import Form, tagged

from odoo.addons.stock_landed_costs.tests.common import TestStockLandedCostsCommon


@tagged('post_install', '-at_install')
class TestStockLandedCosts(TestStockLandedCostsCommon):

    _test_user_groups = None  # FIXME list needed groups

    def test_landed_cost_in_move_line(self):
        """
        Tests that a move line created through the catalog gives the right landed cost
        """
        self.landed_cost.landed_cost_ok = True
        account_move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id
        })
        account_move._update_order_line_info(
            product=self.landed_cost,
            quantity=1,
            uom=self.landed_cost.uom_id,
            child_field='line_ids',
        )
        self.assertTrue(account_move.invoice_line_ids.is_landed_costs_line, "The landed cost should appear in the move line.")
        account_move._update_order_line_info(
            product=self.product,
            quantity=1,
            uom=self.product.uom_id,
            child_field='line_ids',
        )
        move_line_no_landed = account_move.line_ids.filtered(lambda line: line.product_id == self.product)
        self.assertFalse(move_line_no_landed.is_landed_costs_line, "The landed cost should not be set to True.")

    def test_landed_cost_for_specific_products(self):
        """Ensure that landed costs apply only to the products specified in the "Apply On" field
        of the landed cost lines, and exclude all other products from the related pickings.
        """
        self.product_a.is_storable = True
        self.landed_cost.landed_cost_on_product_ids = self.product_refrigerator
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.in_type_id.id,
            'location_id': self.supplier_location_id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
            'move_ids': [
                Command.create({'product_id': product.id, 'product_uom_qty': qty})
                for product, qty in [(self.product_oven, 1), (self.product_refrigerator, 3), (self.product_a, 5)]
            ],
        })
        picking.action_confirm()
        picking.button_validate()

        lc_form = Form(self.env['stock.landed.cost'])
        lc_form.picking_ids.add(picking)
        with lc_form.cost_lines.new() as cost_line:
            cost_line.product_id = self.landed_cost
            cost_line.price_unit = 100
            cost_line.split_method = 'by_quantity'
        lc = lc_form.save()

        self.assertEqual(lc.cost_lines.apply_on_product_ids, self.product_refrigerator)

        lc.cost_lines.write({'apply_on_product_ids': [Command.link(self.product_oven.id)]})
        lc.compute_landed_cost()

        valuation_lines = lc.valuation_adjustment_lines
        self.assertEqual(len(valuation_lines), 2)

        oven_val_line = valuation_lines.filtered(lambda line: line.product_id == self.product_oven)
        refrigerator_val_line = valuation_lines - oven_val_line

        self.assertEqual(oven_val_line.additional_landed_cost, 25)
        self.assertEqual(refrigerator_val_line.additional_landed_cost, 75)
        self.assertFalse(valuation_lines.filtered(lambda line: line.product_id == self.product_a))

    def test_landed_cost_reset_to_draft(self):
        """Resetting a posted landed cost to draft reverses its journal entry and resets the moves values.
        Posting it again creates a new entry and applies the cost again."""
        product = self.product_refrigerator  # AVCO, automated valuation, cost 1
        receipt, delivery = self.Picking.create([{
            'picking_type_id': picking_type.id,
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'move_ids': [Command.create({'product_id': product.id, 'product_uom_qty': quantity})],
        } for picking_type, location_id, location_dest_id, quantity in [
            (self.warehouse.in_type_id, self.supplier_location_id, self.warehouse.lot_stock_id.id, 10),
            (self.warehouse.out_type_id, self.warehouse.lot_stock_id.id, self.customer_location_id, 4),
        ]])
        self._process_pickings(receipt)
        self._process_pickings(delivery)
        moves = receipt.move_ids | delivery.move_ids

        lc = self.LandedCost.create({
            'account_journal_id': self.stock_journal.id,
            'picking_ids': [Command.set(receipt.ids)],
            'cost_lines': [Command.create({
                'product_id': self.landed_cost.id,
                'price_unit': 60,
                'split_method': 'equal',
            })],
        })

        self.assertRecordValues(moves, [{'value': 10}, {'value': -4}])
        self.assertEqual(product.standard_price, 1)

        lc.button_validate()
        self.assertEqual(lc.state, 'done')
        self.assertEqual(lc.account_move_id.state, 'posted')
        self.assertEqual(sum(lc.account_move_id.line_ids.mapped('debit')), 36)
        self.assertRecordValues(moves, [{'value': 70}, {'value': -28}])
        self.assertEqual(product.standard_price, 7)
        first_entry = lc.account_move_id

        # resetting the LC to draft reverses its entry and removes the link to it
        lc.button_reset_to_draft()
        self.assertEqual(lc.state, 'draft')
        self.assertFalse(lc.account_move_id)
        reversal = first_entry.reversal_move_ids
        self.assertEqual(reversal.state, 'posted')
        self.assertRecordValues(moves, [{'value': 10}, {'value': -4}])
        self.assertEqual(product.standard_price, 1)

        # reposting the LC again, creates a new entry
        lc.button_validate()
        self.assertEqual(lc.state, 'done')
        self.assertNotEqual(lc.account_move_id, first_entry)


class TestStockLandedCostsReevaluation(TestStockLandedCostsCommon):

    def test_landed_cost_reevaluates_out_move(self):
        """ Make sure that processing a landed cost after the partial delivery of the quantity received earlier
            correctly updates the delivery values.
        """
        self.product_refrigerator.categ_id.property_cost_method = 'fifo'
        product = self.product_refrigerator
        product.standard_price = 10

        picking_in = self.Picking.create({
            'partner_id': self.supplier_id,
            'picking_type_id': self.warehouse.in_type_id.id,
            'location_id': self.supplier_location_id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
            'move_ids': [Command.create({
                'product_id': product.id,
                'product_uom_qty': 10,
                'uom_id': product.uom_id.id,
                'location_id': self.supplier_location_id,
                'location_dest_id': self.warehouse.lot_stock_id.id,
            })],
        })
        picking_in.action_confirm()
        picking_in.button_validate()

        picking_out = self.Picking.create({
            'partner_id': self.customer_id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.customer_location_id,
            'move_ids': [Command.create({
                'product_id': product.id,
                'product_uom_qty': 3,
                'uom_id': product.uom_id.id,
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.customer_location_id,
            })],
        })
        picking_out.action_confirm()
        picking_out.action_assign()
        picking_out.button_validate()
        out_move = picking_out.move_ids
        self.assertEqual(out_move.value, -30)

        landed_cost = self.LandedCost.create({
            'picking_ids': [Command.set(picking_in.ids)],
            'account_journal_id': self.expenses_journal.id,
            'cost_lines': [Command.create({
                'name': 'equal split',
                'split_method': 'equal',
                'price_unit': 20,
                'product_id': self.landed_cost.id,
            })],
        })
        landed_cost.compute_landed_cost()
        landed_cost.button_validate()

        self.assertEqual(out_move.value, -36)
