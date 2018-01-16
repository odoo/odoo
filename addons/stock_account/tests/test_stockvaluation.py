# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestStockValuation(TransactionCase):
    def setUp(self):
        super(TestStockValuation, self).setUp()
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.partner = self.env['res.partner'].create({'name': 'xxx'})
        self.owner1 = self.env['res.partner'].create({'name': 'owner1'})
        self.uom_unit = self.env.ref('product.product_uom_unit')
        self.product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        self.product2 = self.env['product.product'].create({
            'name': 'Product B',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })

        self.product1.product_tmpl_id.valuation = 'real_time'
        self.product2.product_tmpl_id.valuation = 'real_time'
        Account = self.env['account.account']
        self.stock_input_account = Account.create({
            'name': 'Stock Input',
            'code': 'StockIn',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
        })
        self.stock_output_account = Account.create({
            'name': 'Stock Output',
            'code': 'StockOut',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
        })
        self.stock_valuation_account = Account.create({
            'name': 'Stock Valuation',
            'code': 'Stock Valuation',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
        })
        self.stock_journal = self.env['account.journal'].create({
            'name': 'Stock Journal',
            'code': 'STJTEST',
            'type': 'general',
        })
        self.product1.categ_id.write({
            'property_stock_account_input_categ_id': self.stock_input_account.id,
            'property_stock_account_output_categ_id': self.stock_output_account.id,
            'property_stock_valuation_account_id': self.stock_valuation_account.id,
            'property_stock_journal': self.stock_journal.id,
        })
        self.product1.categ_id.write({
            'property_stock_account_input_categ_id': self.stock_input_account.id,
            'property_stock_account_output_categ_id': self.stock_output_account.id,
            'property_stock_valuation_account_id': self.stock_valuation_account.id,
            'property_stock_journal': self.stock_journal.id,
        })

    def _get_stock_input_move_lines(self):
        return self.env['account.move.line'].search([
            ('account_id', '=', self.stock_input_account.id),
        ], order='date, id')

    def _get_stock_output_move_lines(self):
        return self.env['account.move.line'].search([
            ('account_id', '=', self.stock_output_account.id),
        ], order='date, id')

    def _get_stock_valuation_move_lines(self):
        return self.env['account.move.line'].search([
            ('account_id', '=', self.stock_valuation_account.id),
        ], order='date, id')

    def test_fifo_perpetual_1(self):
        self.product1.product_tmpl_id.cost_method = 'fifo'

        # ---------------------------------------------------------------------
        # receive 10 units @ 10.00 per unit
        # ---------------------------------------------------------------------
        move1 = self.env['stock.move'].create({
            'name': 'IN 10 units @ 10.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10.0
        move1._action_done()

        # stock_account values for move1
        self.assertEqual(move1.product_uom_qty, 10.0)
        self.assertEqual(move1.price_unit, 10.0)
        self.assertEqual(move1.remaining_qty, 10.0)
        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_value, 100.0)

        # account values for move1
        input_aml = self._get_stock_input_move_lines()
        self.assertEqual(len(input_aml), 1)
        move1_input_aml = input_aml[-1]
        self.assertEqual(move1_input_aml.debit, 0)
        self.assertEqual(move1_input_aml.credit, 100)

        valuation_aml = self._get_stock_valuation_move_lines()
        move1_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 1)
        self.assertEqual(move1_valuation_aml.debit, 100)
        self.assertEqual(move1_valuation_aml.credit, 0)

        output_aml = self._get_stock_output_move_lines()
        self.assertEqual(len(output_aml), 0)

        # link between stock move and account move
        self.assertEqual(len(move1.account_move_ids), 1)
        self.assertTrue(set(move1.account_move_ids.line_ids.ids) == {move1_valuation_aml.id, move1_input_aml.id})

        # ---------------------------------------------------------------------
        # receive 10 units @ 8.00 per unit
        # ---------------------------------------------------------------------
        move2 = self.env['stock.move'].create({
            'name': 'IN 10 units @ 8.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 8.0,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 10.0
        move2._action_done()

        # stock_account values for move2
        self.assertEqual(move2.product_uom_qty, 10.0)
        self.assertEqual(move2.price_unit, 8.0)
        self.assertEqual(move2.remaining_qty, 10.0)
        self.assertEqual(move2.value, 80.0)
        self.assertEqual(move2.remaining_value, 80.0)

        # account values for move2
        input_aml = self._get_stock_input_move_lines()
        self.assertEqual(len(input_aml), 2)
        move2_input_aml = input_aml[-1]
        self.assertEqual(move2_input_aml.debit, 0)
        self.assertEqual(move2_input_aml.credit, 80)

        valuation_aml = self._get_stock_valuation_move_lines()
        move2_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 2)
        self.assertEqual(move2_valuation_aml.debit, 80)
        self.assertEqual(move2_valuation_aml.credit, 0)

        output_aml = self._get_stock_output_move_lines()
        self.assertEqual(len(output_aml), 0)

        # link between stock move and account move
        self.assertEqual(len(move2.account_move_ids), 1)
        self.assertTrue(set(move2.account_move_ids.line_ids.ids) == {move2_valuation_aml.id, move2_input_aml.id})

        # older moves
        self.assertEqual(move1.product_uom_qty, 10.0)
        self.assertEqual(move1.price_unit, 10.0)
        self.assertEqual(move1.remaining_qty, 10.0)
        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_value, 100.0)
        self.assertEqual(len(move1.account_move_ids), 1)
        self.assertTrue(set(move1.account_move_ids.line_ids.ids) == {move1_valuation_aml.id, move1_input_aml.id})

        # ---------------------------------------------------------------------
        # sale 3 units
        # ---------------------------------------------------------------------
        move3 = self.env['stock.move'].create({
            'name': 'Sale 3 units',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 3.0,
        })
        move3._action_confirm()
        move3._action_assign()
        move3.move_line_ids.qty_done = 3.0
        move3._action_done()

        # stock_account values for move3
        self.assertEqual(move3.product_uom_qty, 3.0)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out move
        self.assertEqual(move3.value, -30.0)  # took 3 items from move 1 @ 10.00 per unit
        self.assertEqual(move3.remaining_value, 0.0)  # took 3 items from move 1 @ 10.00 per unit

        # account values for move3
        input_aml = self._get_stock_input_move_lines()
        self.assertEqual(len(input_aml), 2)

        valuation_aml = self._get_stock_valuation_move_lines()
        move3_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 3)
        self.assertEqual(move3_valuation_aml.debit, 0)
        self.assertEqual(move3_valuation_aml.credit, 30)

        output_aml = self._get_stock_output_move_lines()
        move3_output_aml = output_aml[-1]
        self.assertEqual(len(output_aml), 1)
        self.assertEqual(move3_output_aml.debit, 30)
        self.assertEqual(move3_output_aml.credit, 0)

        # link between stock move and account move
        self.assertEqual(len(move3.account_move_ids), 1)
        self.assertTrue(set(move3.account_move_ids.line_ids.ids) == {move3_valuation_aml.id, move3_output_aml.id})

        # older moves
        self.assertEqual(move1.product_uom_qty, 10.0)
        self.assertEqual(move1.price_unit, 10.0)
        self.assertEqual(move1.remaining_qty, 7)
        self.assertEqual(move1.remaining_value, 70)
        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move2.product_uom_qty, 10.0)
        self.assertEqual(move2.price_unit, 8.0)
        self.assertEqual(move2.remaining_qty, 10.0)
        self.assertEqual(move2.value, 80.0)
        self.assertEqual(move2.remaining_value, 80.0)
        self.assertTrue(set(move1.account_move_ids.line_ids.ids) == {move1_valuation_aml.id, move1_input_aml.id})
        self.assertTrue(set(move2.account_move_ids.line_ids.ids) == {move2_valuation_aml.id, move2_input_aml.id})

        # ---------------------------------------------------------------------
        # Increase received quantity of move1 from 10 to 12, it should updates
        # the remaining quantity, the value and remaining value on this move
        # without impacting any of the next ones.
        # ---------------------------------------------------------------------
        move1.quantity_done = 12

        # stock_account values for move3
        self.assertEqual(move1.product_uom_qty, 12.0)
        self.assertEqual(move1.price_unit, 10.0)
        self.assertEqual(move1.remaining_qty, 9.0)
        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_value, 90.0)

        # account values for move1
        input_aml = self._get_stock_input_move_lines()
        self.assertEqual(len(input_aml), 3)
        move1_correction_input_aml = input_aml[-1]
        self.assertEqual(move1_correction_input_aml.debit, 0)
        self.assertEqual(move1_correction_input_aml.credit, 20)

        valuation_aml = self._get_stock_valuation_move_lines()
        move1_correction_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 4)
        self.assertEqual(move1_correction_valuation_aml.debit, 20)
        self.assertEqual(move1_correction_valuation_aml.credit, 0)

        output_aml = self._get_stock_output_move_lines()
        self.assertEqual(len(output_aml), 1)

        # link between stock move and account move
        self.assertEqual(len(move1.account_move_ids), 2)
        self.assertTrue(set(move1.account_move_ids.mapped('line_ids').ids) == {move1_input_aml.id, move1_valuation_aml.id, move1_correction_input_aml.id, move1_correction_valuation_aml.id})

        # older moves
        self.assertEqual(move2.product_uom_qty, 10.0)
        self.assertEqual(move2.price_unit, 8.0)
        self.assertEqual(move2.remaining_qty, 10.0)
        self.assertEqual(move2.value, 80.0)
        self.assertEqual(move2.remaining_value, 80.0)
        self.assertEqual(move3.product_uom_qty, 3.0)
        self.assertEqual(move3.remaining_qty, 0.0)
        self.assertEqual(move3.value, -30.0)
        self.assertEqual(move3.remaining_value, 0.0)
        self.assertTrue(set(move2.account_move_ids.line_ids.ids) == {move2_valuation_aml.id, move2_input_aml.id})
        self.assertTrue(set(move3.account_move_ids.line_ids.ids) == {move3_valuation_aml.id, move3_output_aml.id})

        # ---------------------------------------------------------------------
        # Sale 9 units, the units available from the previous increase are sent
        # immediately.
        # ---------------------------------------------------------------------
        move4 = self.env['stock.move'].create({
            'name': 'Sale 9 units',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 9.0,
        })
        move4._action_confirm()
        move4._action_assign()
        move4.move_line_ids.qty_done = 9.0
        move4._action_done()

        # stock_account values for move4
        self.assertEqual(move4.product_uom_qty, 9.0)
        self.assertEqual(move4.remaining_qty, 0.0)  # unused in out move
        self.assertEqual(move4.value, -90.0)  # took 9 items from move 1 @ 10.00 per unit
        self.assertEqual(move4.remaining_value, 0.0)  # took 3 items from move 1 @ 10.00 per unit

        # account values for move4
        input_aml = self._get_stock_input_move_lines()
        self.assertEqual(len(input_aml), 3)

        valuation_aml = self._get_stock_valuation_move_lines()
        move4_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 5)
        self.assertEqual(move4_valuation_aml.debit, 0)
        self.assertEqual(move4_valuation_aml.credit, 90)

        output_aml = self._get_stock_output_move_lines()
        move4_output_aml = output_aml[-1]
        self.assertEqual(len(output_aml), 2)
        self.assertEqual(move4_output_aml.debit, 90)
        self.assertEqual(move4_output_aml.credit, 0)

        # link between stock move and account move
        self.assertEqual(len(move4.account_move_ids), 1)
        self.assertTrue(set(move4.account_move_ids.line_ids.ids) == {move4_valuation_aml.id, move4_output_aml.id})

        # older moves
        self.assertEqual(move1.product_uom_qty, 12)
        self.assertEqual(move1.price_unit, 10.0)
        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move1.value, 100)
        self.assertEqual(move1.remaining_value, 0)
        self.assertEqual(move2.product_uom_qty, 10.0)
        self.assertEqual(move2.price_unit, 8.0)
        self.assertEqual(move2.remaining_qty, 10.0)
        self.assertEqual(move2.value, 80.0)
        self.assertEqual(move2.remaining_value, 80.0)
        self.assertEqual(move3.product_uom_qty, 3.0)
        self.assertEqual(move3.remaining_qty, 0.0)
        self.assertEqual(move3.value, -30.0)
        self.assertEqual(move3.remaining_value, 0.0)
        self.assertTrue(set(move1.account_move_ids.mapped('line_ids').ids) == {move1_input_aml.id, move1_valuation_aml.id, move1_correction_input_aml.id, move1_correction_valuation_aml.id})
        self.assertTrue(set(move2.account_move_ids.line_ids.ids) == {move2_valuation_aml.id, move2_input_aml.id})
        self.assertTrue(set(move3.account_move_ids.line_ids.ids) == {move3_valuation_aml.id, move3_output_aml.id})

        # ---------------------------------------------------------------------
        # Sale 20 units, we fall in negative stock for 10 units. Theses are
        # valued at the last FIFO cost and the total is negative.
        # ---------------------------------------------------------------------
        move5 = self.env['stock.move'].create({
            'name': 'Sale 20 units',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 20.0,
        })
        move5._action_confirm()
        move5._action_assign()
        move5.move_line_ids.qty_done = 20.0
        move5._action_done()

        # stock_account values for move5
        self.assertEqual(move5.product_uom_qty, 20.0)
        self.assertEqual(move5.remaining_qty, -10.0)
        self.assertEqual(move5.value, -160.0)
        self.assertEqual(move5.remaining_value, -80.0)

        # account values for move5
        input_aml = self._get_stock_input_move_lines()
        self.assertEqual(len(input_aml), 3)

        valuation_aml = self._get_stock_valuation_move_lines()
        move5_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 6)
        self.assertEqual(move5_valuation_aml.debit, 0)
        self.assertEqual(move5_valuation_aml.credit, 160)

        output_aml = self._get_stock_output_move_lines()
        move5_output_aml = output_aml[-1]
        self.assertEqual(len(output_aml), 3)
        self.assertEqual(move5_output_aml.debit, 160)
        self.assertEqual(move5_output_aml.credit, 0)

        # link between stock move and account move
        self.assertEqual(len(move5.account_move_ids), 1)
        self.assertTrue(set(move5.account_move_ids.line_ids.ids) == {move5_valuation_aml.id, move5_output_aml.id})

        # older moves
        self.assertEqual(move1.product_uom_qty, 12)
        self.assertEqual(move1.price_unit, 10.0)
        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move1.value, 100)
        self.assertEqual(move1.remaining_value, 0)
        self.assertEqual(move2.product_uom_qty, 10.0)
        self.assertEqual(move2.price_unit, 8.0)
        self.assertEqual(move2.remaining_qty, 0)
        self.assertEqual(move2.value, 80.0)
        self.assertEqual(move2.remaining_value, 0)
        self.assertEqual(move3.product_uom_qty, 3.0)
        self.assertEqual(move3.remaining_qty, 0.0)
        self.assertEqual(move3.value, -30.0)
        self.assertEqual(move3.remaining_value, 0.0)
        self.assertEqual(move4.product_uom_qty, 9.0)
        self.assertEqual(move4.remaining_qty, 0.0)
        self.assertEqual(move4.value, -90.0)
        self.assertEqual(move4.remaining_value, 0)
        self.assertTrue(set(move1.account_move_ids.mapped('line_ids').ids) == {move1_input_aml.id, move1_valuation_aml.id, move1_correction_input_aml.id, move1_correction_valuation_aml.id})
        self.assertTrue(set(move2.account_move_ids.line_ids.ids) == {move2_valuation_aml.id, move2_input_aml.id})
        self.assertTrue(set(move3.account_move_ids.line_ids.ids) == {move3_valuation_aml.id, move3_output_aml.id})
        self.assertTrue(set(move4.account_move_ids.line_ids.ids) == {move4_valuation_aml.id, move4_output_aml.id})

        # ---------------------------------------------------------------------
        # Receive 10 units @ 12.00 to counterbalance the negative, we do not do
        # the operation right now.
        # ---------------------------------------------------------------------
        move6 = self.env['stock.move'].create({
            'name': 'IN 10 units @ 12.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 12.0,
        })
        move6._action_confirm()
        move6._action_assign()
        move6.move_line_ids.qty_done = 10.0
        move6._action_done()

        # stock_account values for move6
        self.assertEqual(move6.product_uom_qty, 10)
        self.assertEqual(move6.price_unit, 12.0)
        self.assertEqual(move6.remaining_qty, 10.0)
        self.assertEqual(move6.value, 120)
        self.assertEqual(move6.remaining_value, 120)

        # account values for move6
        input_aml = self._get_stock_input_move_lines()
        move6_input_aml = input_aml[-1]
        self.assertEqual(len(input_aml), 4)
        self.assertEqual(move6_input_aml.debit, 0)
        self.assertEqual(move6_input_aml.credit, 120)

        valuation_aml = self._get_stock_valuation_move_lines()
        move6_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 7)
        self.assertEqual(move6_valuation_aml.debit, 120)
        self.assertEqual(move6_valuation_aml.credit, 0)

        output_aml = self._get_stock_output_move_lines()
        self.assertEqual(len(output_aml), 3)

        # link between stock move and account move
        self.assertEqual(len(move6.account_move_ids), 1)
        self.assertTrue(set(move6.account_move_ids.line_ids.ids) == {move6_valuation_aml.id, move6_input_aml.id})

        # older moves
        self.assertEqual(move1.product_uom_qty, 12)
        self.assertEqual(move1.price_unit, 10.0)
        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move1.value, 100)
        self.assertEqual(move1.remaining_value, 0)
        self.assertEqual(move2.product_uom_qty, 10.0)
        self.assertEqual(move2.price_unit, 8.0)
        self.assertEqual(move2.remaining_qty, 0)
        self.assertEqual(move2.value, 80.0)
        self.assertEqual(move2.remaining_value, 0)
        self.assertEqual(move3.product_uom_qty, 3.0)
        self.assertEqual(move3.remaining_qty, 0.0)
        self.assertEqual(move3.value, -30.0)
        self.assertEqual(move3.remaining_value, 0.0)
        self.assertEqual(move4.product_uom_qty, 9.0)
        self.assertEqual(move4.remaining_qty, 0.0)
        self.assertEqual(move4.value, -90.0)
        self.assertEqual(move4.remaining_value, 0)
        self.assertEqual(move5.product_uom_qty, 20.0)
        self.assertEqual(move5.remaining_qty, -10.0)
        self.assertEqual(move5.value, -160.0)
        self.assertEqual(move5.remaining_value, -80.0)
        self.assertTrue(set(move1.account_move_ids.mapped('line_ids').ids) == {move1_input_aml.id, move1_valuation_aml.id, move1_correction_input_aml.id, move1_correction_valuation_aml.id})
        self.assertTrue(set(move2.account_move_ids.line_ids.ids) == {move2_valuation_aml.id, move2_input_aml.id})
        self.assertTrue(set(move3.account_move_ids.line_ids.ids) == {move3_valuation_aml.id, move3_output_aml.id})
        self.assertTrue(set(move4.account_move_ids.line_ids.ids) == {move4_valuation_aml.id, move4_output_aml.id})
        self.assertTrue(set(move5.account_move_ids.line_ids.ids) == {move5_valuation_aml.id, move5_output_aml.id})

        # ---------------------------------------------------------------------
        # Vacuum is called, we cleanup the negatives.
        # ---------------------------------------------------------------------
        self.env['stock.move']._run_fifo_vacuum()

        # account values after vacuum
        input_aml = self._get_stock_input_move_lines()
        self.assertEqual(len(input_aml), 4)

        valuation_aml = self._get_stock_valuation_move_lines()
        vacuum_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 8)
        self.assertEqual(vacuum_valuation_aml.balance, -40)

        output_aml = self._get_stock_output_move_lines()
        vacuum_output_aml = output_aml[-1]
        self.assertEqual(len(output_aml), 4)
        self.assertEqual(vacuum_output_aml.balance, 40)

        # stock_account values
        self.assertEqual(move1.product_uom_qty, 12)
        self.assertEqual(move1.price_unit, 10.0)
        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move1.value, 100)
        self.assertEqual(move1.remaining_value, 0)
        self.assertEqual(move2.product_uom_qty, 10.0)
        self.assertEqual(move2.price_unit, 8.0)
        self.assertEqual(move2.remaining_qty, 0)
        self.assertEqual(move2.value, 80.0)
        self.assertEqual(move2.remaining_value, 0)
        self.assertEqual(move3.product_uom_qty, 3.0)
        self.assertEqual(move3.remaining_qty, 0.0)
        self.assertEqual(move3.value, -30.0)
        self.assertEqual(move3.remaining_value, 0.0)
        self.assertEqual(move4.product_uom_qty, 9.0)
        self.assertEqual(move4.remaining_qty, 0.0)
        self.assertEqual(move4.value, -90.0)
        self.assertEqual(move4.remaining_value, 0)
        self.assertEqual(move5.product_uom_qty, 20.0)
        self.assertEqual(move5.remaining_qty, 0.0)
        self.assertEqual(move5.value, -160.0)
        self.assertEqual(move5.remaining_value, 0.0)
        self.assertEqual(move6.product_uom_qty, 10)
        self.assertEqual(move6.price_unit, 12.0)
        self.assertEqual(move6.remaining_qty, 0.0)
        self.assertEqual(move6.value, 120)
        self.assertEqual(move6.remaining_value, 0)
        self.assertTrue(set(move1.account_move_ids.mapped('line_ids').ids) == {move1_input_aml.id, move1_valuation_aml.id, move1_correction_input_aml.id, move1_correction_valuation_aml.id})
        self.assertTrue(set(move2.account_move_ids.line_ids.ids) == {move2_valuation_aml.id, move2_input_aml.id})
        self.assertTrue(set(move3.account_move_ids.line_ids.ids) == {move3_valuation_aml.id, move3_output_aml.id})
        self.assertTrue(set(move4.account_move_ids.line_ids.ids) == {move4_valuation_aml.id, move4_output_aml.id})
        # a new account move was created  for move 5, to compensate the negative stock we had
        move5_correction_account_move = self.env['account.move'].browse(max(move5.account_move_ids.ids))
        move5_correction_output_aml = move5_correction_account_move.line_ids.filtered(lambda ml: ml.account_id == self.stock_output_account)
        self.assertEqual(move5_correction_output_aml.debit, 40)
        self.assertEqual(move5_correction_output_aml.credit, 0)
        move5_correction_valuation_aml = move5_correction_account_move.line_ids.filtered(lambda ml: ml.account_id == self.stock_valuation_account)
        self.assertEqual(move5_correction_valuation_aml.debit, 0)
        self.assertEqual(move5_correction_valuation_aml.credit, 40)
        self.assertTrue(set(move5.account_move_ids.mapped('line_ids').ids) == {move5_valuation_aml.id, move5_output_aml.id, move5_correction_output_aml.id, move5_correction_valuation_aml.id})
        self.assertTrue(set(move6.account_move_ids.line_ids.ids) == {move6_valuation_aml.id, move6_input_aml.id})

        # ---------------------------------------------------------------------
        # Edit move6, receive less
        # ---------------------------------------------------------------------
        move6.quantity_done = 8

        # stock_account values for move6
        self.assertEqual(move6.product_uom_qty, 8)
        self.assertEqual(move6.price_unit, 12)
        self.assertEqual(move6.remaining_qty, -2)
        self.assertEqual(move6.value, 120)
        self.assertEqual(move6.remaining_value, -24)

        # account values for move1
        input_aml = self._get_stock_input_move_lines()
        move6_correction_input_aml = input_aml[-1]
        self.assertEqual(move6_correction_input_aml.debit, 24)
        self.assertEqual(move6_correction_input_aml.credit, 0)

        valuation_aml = self._get_stock_valuation_move_lines()
        move6_correction_valuation_aml = valuation_aml[-1]
        self.assertEqual(move6_correction_valuation_aml.debit, 0)
        self.assertEqual(move6_correction_valuation_aml.credit, 24)

        # link between stock move and account move
        self.assertEqual(len(move6.account_move_ids), 2)
        self.assertTrue(set(move6.account_move_ids.mapped('line_ids').ids) == {move6_input_aml.id, move6_valuation_aml.id, move6_correction_input_aml.id, move6_correction_valuation_aml.id})

        # -----------------------------------------------------------
        # receive 4, do not counterbalance now
        # -----------------------------------------------------------
        move7 = self.env['stock.move'].create({
            'name': 'IN 4 units @ 15.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4.0,
            'price_unit': 15.0,
        })
        move7._action_confirm()
        move7._action_assign()
        move7.move_line_ids.qty_done = 4.0
        move7._action_done()

        # stock_account values for move1
        self.assertEqual(move7.product_uom_qty, 4.0)
        self.assertEqual(move7.price_unit, 15.0)
        self.assertEqual(move7.remaining_qty, 4.0)
        self.assertEqual(move7.value, 60.0)
        self.assertEqual(move7.remaining_value, 60.0)

        # account values for move7
        input_aml = self._get_stock_input_move_lines()
        self.assertEqual(len(input_aml), 6)
        move7_input_aml = input_aml[-1]
        self.assertEqual(move7_input_aml.debit, 0)
        self.assertEqual(move7_input_aml.credit, 60)

        valuation_aml = self._get_stock_valuation_move_lines()
        move7_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 10)
        self.assertEqual(move7_valuation_aml.debit, 60)
        self.assertEqual(move7_valuation_aml.credit, 0)

        # link between stock move and account move
        self.assertEqual(len(move7.account_move_ids), 1)
        self.assertTrue(set(move7.account_move_ids.line_ids.ids) == {move7_valuation_aml.id, move7_input_aml.id})

        # -----------------------------------------------------------
        # vacuum, compensate in
        # -----------------------------------------------------------
        self.env['stock.move']._run_fifo_vacuum()

        # account values after vacuum
        input_aml = self._get_stock_input_move_lines()
        self.assertEqual(len(input_aml), 7)
        move6_correction2_input_aml = input_aml[-1]
        self.assertEqual(move6_correction2_input_aml.debit, 6)
        self.assertEqual(move6_correction2_input_aml.credit, 0)

        valuation_aml = self._get_stock_valuation_move_lines()
        move6_correction2_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 11)
        self.assertEqual(move6_correction2_valuation_aml.debit, 0)
        self.assertEqual(move6_correction2_valuation_aml.credit, 6)

        # stock_account values
        self.assertEqual(move1.product_uom_qty, 12)
        self.assertEqual(move1.price_unit, 10.0)
        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move1.value, 100)
        self.assertEqual(move1.remaining_value, 0)
        self.assertEqual(move2.product_uom_qty, 10.0)
        self.assertEqual(move2.price_unit, 8.0)
        self.assertEqual(move2.remaining_qty, 0)
        self.assertEqual(move2.value, 80.0)
        self.assertEqual(move2.remaining_value, 0)
        self.assertEqual(move3.product_uom_qty, 3.0)
        self.assertEqual(move3.remaining_qty, 0.0)
        self.assertEqual(move3.value, -30.0)
        self.assertEqual(move3.remaining_value, 0.0)
        self.assertEqual(move4.product_uom_qty, 9.0)
        self.assertEqual(move4.remaining_qty, 0.0)
        self.assertEqual(move4.value, -90.0)
        self.assertEqual(move4.remaining_value, 0)
        self.assertEqual(move5.product_uom_qty, 20.0)
        self.assertEqual(move5.remaining_qty, 0.0)
        self.assertEqual(move5.value, -160.0)
        self.assertEqual(move5.remaining_value, 0.0)
        self.assertEqual(move6.product_uom_qty, 8)
        self.assertEqual(move6.price_unit, 12.0)
        self.assertEqual(move6.remaining_qty, 0.0)
        self.assertEqual(move6.value, 120)
        self.assertEqual(move6.remaining_value, 0)
        self.assertEqual(move7.product_uom_qty, 4.0)
        self.assertEqual(move7.price_unit, 15.0)
        self.assertEqual(move7.remaining_qty, 2.0)
        self.assertEqual(move7.value, 60.0)
        self.assertEqual(move7.remaining_value, 30.0)
        self.assertTrue(set(move1.account_move_ids.mapped('line_ids').ids) == {move1_input_aml.id, move1_valuation_aml.id, move1_correction_input_aml.id, move1_correction_valuation_aml.id})
        self.assertTrue(set(move2.account_move_ids.line_ids.ids) == {move2_valuation_aml.id, move2_input_aml.id})
        self.assertTrue(set(move3.account_move_ids.line_ids.ids) == {move3_valuation_aml.id, move3_output_aml.id})
        self.assertTrue(set(move4.account_move_ids.line_ids.ids) == {move4_valuation_aml.id, move4_output_aml.id})
        # a new account move was created  for move 5, to compensate the negative stock we had
        move5_correction_account_move = self.env['account.move'].browse(max(move5.account_move_ids.ids))
        move5_correction_output_aml = move5_correction_account_move.line_ids.filtered(lambda ml: ml.account_id == self.stock_output_account)
        self.assertEqual(move5_correction_output_aml.debit, 40)
        self.assertEqual(move5_correction_output_aml.credit, 0)
        move5_correction_valuation_aml = move5_correction_account_move.line_ids.filtered(lambda ml: ml.account_id == self.stock_valuation_account)
        self.assertEqual(move5_correction_valuation_aml.debit, 0)
        self.assertEqual(move5_correction_valuation_aml.credit, 40)
        self.assertTrue(set(move5.account_move_ids.mapped('line_ids').ids) == {move5_valuation_aml.id, move5_output_aml.id, move5_correction_output_aml.id, move5_correction_valuation_aml.id})
        self.assertTrue(set(move6.account_move_ids.mapped('line_ids').ids) == {move6_valuation_aml.id, move6_input_aml.id, move6_correction_input_aml.id, move6_correction_valuation_aml.id, move6_correction2_input_aml.id, move6_correction2_valuation_aml.id})

        # ---------------------------------------------------------------------
        # Ending
        # ---------------------------------------------------------------------
        self.assertEqual(self.product1.qty_available, 2)
        self.assertEqual(self.product1.stock_value, 30)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('debit')), 30)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('credit')), 380)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 380)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 350)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('debit')), 320)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('credit')), 0)

    def test_fifo_perpetual_2(self):
        # http://accountingexplained.com/financial/inventories/fifo-method
        self.product1.product_tmpl_id.cost_method = 'fifo'

        # Beginning Inventory: 68 units @ 15.00 per unit
        move1 = self.env['stock.move'].create({
            'name': '68 units @ 15.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 68.0,
            'price_unit': 15,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 68.0
        move1._action_done()

        self.assertEqual(move1.value, 1020.0)

        self.assertEqual(move1.remaining_qty, 68.0)

        # Purchase 140 units @ 15.50 per unit
        move2 = self.env['stock.move'].create({
            'name': '140 units @ 15.50 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 140.0,
            'price_unit': 15.50,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 140.0
        move2._action_done()

        self.assertEqual(move2.value, 2170.0)

        self.assertEqual(move1.remaining_qty, 68.0)
        self.assertEqual(move2.remaining_qty, 140.0)

        # Sale 94 units @ 19.00 per unit
        move3 = self.env['stock.move'].create({
            'name': 'Sale 94 units @ 19.00 per unit',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 94.0,
        })
        move3._action_confirm()
        move3._action_assign()
        move3.move_line_ids.qty_done = 94.0
        move3._action_done()


        # note: it' ll have to get 68 units from the first batch and 26 from the second one
        # so its value should be -((68*15) + (26*15.5)) = -1423
        self.assertEqual(move3.value, -1423.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 114)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out moves

        # Purchase 40 units @ 16.00 per unit
        move4 = self.env['stock.move'].create({
            'name': '140 units @ 15.50 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 40.0,
            'price_unit': 16,
        })
        move4._action_confirm()
        move4._action_assign()
        move4.move_line_ids.qty_done = 40.0
        move4._action_done()

        self.assertEqual(move4.value, 640.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 114)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.remaining_qty, 40.0)

        # Purchase 78 units @ 16.50 per unit
        move5 = self.env['stock.move'].create({
            'name': 'Purchase 78 units @ 16.50 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 78.0,
            'price_unit': 16.5,
        })
        move5._action_confirm()
        move5._action_assign()
        move5.move_line_ids.qty_done = 78.0
        move5._action_done()

        self.assertEqual(move5.value, 1287.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 114)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.remaining_qty, 40.0)
        self.assertEqual(move5.remaining_qty, 78.0)

        # Sale 116 units @ 19.50 per unit
        move6 = self.env['stock.move'].create({
            'name': 'Sale 116 units @ 19.50 per unit',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 116.0,
        })
        move6._action_confirm()
        move6._action_assign()
        move6.move_line_ids.qty_done = 116.0
        move6._action_done()

        # note: it' ll have to get 114 units from the move2 and 2 from move4
        # so its value should be -((114*15.5) + (2*16)) = 1735
        self.assertEqual(move6.value, -1799.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 0)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.remaining_qty, 38.0)
        self.assertEqual(move5.remaining_qty, 78.0)
        self.assertEqual(move6.remaining_qty, 0.0)  # unused in out moves

        # Sale 62 units @ 21 per unit
        move7 = self.env['stock.move'].create({
            'name': 'Sale 62 units @ 21 per unit',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 62.0,
        })
        move7._action_confirm()
        move7._action_assign()
        move7.move_line_ids.qty_done = 62.0
        move7._action_done()

        # note: it' ll have to get 38 units from the move4 and 24 from move5
        # so its value should be -((38*16) + (24*16.5)) = 608 + 396
        self.assertEqual(move7.value, -1004.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 0)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.remaining_qty, 0.0)
        self.assertEqual(move5.remaining_qty, 54.0)
        self.assertEqual(move6.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move7.remaining_qty, 0.0)  # unused in out moves

        # send 10 units in our transit location, the valorisation should not be impacted
        transit_location = self.env['stock.location'].search([
            ('company_id', '=', self.env.user.company_id.id),
            ('usage', '=', 'transit'),
        ], limit=1)
        move8 = self.env['stock.move'].create({
            'name': 'Send 10 units in transit',
            'location_id': self.stock_location.id,
            'location_dest_id': transit_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move8._action_confirm()
        move8._action_assign()
        move8.move_line_ids.qty_done = 10.0
        move8._action_done()

        self.assertEqual(move8.value, 0.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 0)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.remaining_qty, 0.0)
        self.assertEqual(move5.remaining_qty, 54.0)
        self.assertEqual(move6.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move7.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move8.remaining_qty, 0.0)  # unused in internal moves

        # Sale 10 units @ 16.5 per unit
        move9 = self.env['stock.move'].create({
            'name': 'Sale 10 units @ 16.5 per unit',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move9._action_confirm()
        move9._action_assign()
        move9.move_line_ids.qty_done = 10.0
        move9._action_done()

        # note: it' ll have to get 10 units from move5 so its value should
        # be -(10*16.50) = -165
        self.assertEqual(move9.value, -165.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 0)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.remaining_qty, 0.0)
        self.assertEqual(move5.remaining_qty, 44.0)
        self.assertEqual(move6.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move7.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move8.remaining_qty, 0.0)  # unused in internal moves
        self.assertEqual(move9.remaining_qty, 0.0)  # unused in out moves

    def test_fifo_perpetual_3(self):
        self.product1.cost_method = 'fifo'

        # in 10 @ 100
        move1 = self.env['stock.move'].create({
            'name': 'in 10 @ 100',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 100,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10.0
        move1._action_done()

        self.assertEqual(move1.value, 1000.0)

        self.assertEqual(move1.remaining_qty, 10.0)

        # in 10 @ 80
        move2 = self.env['stock.move'].create({
            'name': 'in 10 @ 80',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 80,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 10.0
        move2._action_done()

        self.assertEqual(move2.value, 800.0)

        self.assertEqual(move1.remaining_qty, 10.0)
        self.assertEqual(move2.remaining_qty, 10.0)

        # out 15
        move3 = self.env['stock.move'].create({
            'name': 'out 15',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 15.0,
        })
        move3._action_confirm()
        move3._action_assign()
        move3.move_line_ids.qty_done = 15.0
        move3._action_done()


        # note: it' ll have to get 10 units from move1 and 5 from move2
        # so its value should be -((10*100) + (5*80)) = -1423
        self.assertEqual(move3.value, -1400.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 5)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out moves

        # in 5 @ 60
        move4 = self.env['stock.move'].create({
            'name': 'in 5 @ 60',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
            'price_unit': 60,
        })
        move4._action_confirm()
        move4._action_assign()
        move4.move_line_ids.qty_done = 5.0
        move4._action_done()

        self.assertEqual(move4.value, 300.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 5)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.remaining_qty, 5.0)

        # out 7
        move5 = self.env['stock.move'].create({
            'name': 'out 7',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 7.0,
        })
        move5._action_confirm()
        move5._action_assign()
        move5.move_line_ids.qty_done = 7.0
        move5._action_done()

        # note: it' ll have to get 5 units from the move2 and 2 from move4
        # so its value should be -((5*80) + (2*60)) = 520
        self.assertEqual(move5.value, -520.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 0)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.remaining_qty, 3.0)
        self.assertEqual(move5.remaining_qty, 0.0)  # unused in out moves

    def test_fifo_perpetual_4(self):
        """ Fifo and return handling.
        """
        self.product1.cost_method = 'fifo'

        # in 8 @ 10
        move1 = self.env['stock.move'].create({
            'name': 'in 8 @ 10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 8.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 8.0
        move1._action_done()

        self.assertEqual(move1.value, 80.0)
        self.assertEqual(move1.remaining_value, 80.0)
        self.assertEqual(move1.remaining_qty, 8.0)

        # in 4 @ 16
        move2 = self.env['stock.move'].create({
            'name': 'in 4 @ 16',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4.0,
            'price_unit': 16,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 4.0
        move2._action_done()


        self.assertEqual(move2.value, 64)
        self.assertEqual(move2.remaining_value, 64)
        self.assertEqual(move2.remaining_qty, 4.0)

        # out 10
        out_pick = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'partner_id': self.env['res.partner'].search([], limit=1).id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move3 = self.env['stock.move'].create({
            'name': 'out 10',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'picking_id': out_pick.id,
        })
        move3._action_confirm()
        move3._action_assign()
        move3.move_line_ids.qty_done = 10.0
        move3._action_done()


        # note: it' ll have to get 8 units from move1 and 2 from move2
        # so its value should be -((8*10) + (2*16)) = -116
        self.assertEqual(move3.value, -112.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 2)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out moves

        # in 2 @ 6
        move4 = self.env['stock.move'].create({
            'name': 'in 2 @ 6',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
            'price_unit': 6,
        })
        move4._action_confirm()
        move4._action_assign()
        move4.move_line_ids.qty_done = 2.0
        move4._action_done()

        self.assertEqual(move4.value, 12.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 2)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.remaining_qty, 2.0)

        self.assertEqual(self.product1.standard_price, 16)

        # return
        stock_return_picking = self.env['stock.return.picking']\
            .with_context(active_ids=[out_pick.id], active_id=out_pick.id)\
            .create({})
        stock_return_picking.product_return_moves.quantity = 1.0 # Return only 2
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.move_lines[0].move_line_ids[0].qty_done = 1.0
        return_pick.do_transfer()

        self.assertEqual(self.product1.standard_price, 16)

        self.assertEqual(return_pick.move_lines.price_unit, 16)

    def test_fifo_negative_1(self):
        """ Send products that you do not have. Value the first outgoing move to the standard
        price, receive in multiple times the delivered quantity and run _fifo_vacuum to compensate.
        """
        self.product1.product_tmpl_id.cost_method = 'fifo'

        # We expect the user to set manually set a standard price to its products if its first
        # transfer is sending products that he doesn't have.
        self.product1.product_tmpl_id.standard_price = 8.0

        # ---------------------------------------------------------------------
        # Send 50 units you don't have
        # ---------------------------------------------------------------------
        move1 = self.env['stock.move'].create({
            'name': '50 out',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 50.0,
            'price_unit': 0,
            'move_line_ids': [(0, 0, {
                'product_id': self.product1.id,
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 50.0,
            })]
        })
        move1._action_confirm()
        move1._action_done()

        # stock values for move1
        self.assertEqual(move1.value, -400.0)
        self.assertEqual(move1.remaining_qty, -50.0)  # normally unused in out moves, but as it moved negative stock we mark it
        self.assertEqual(move1.price_unit, -8)
        self.assertEqual(move1.remaining_value, -400.0)

        # account values for move1
        valuation_aml = self._get_stock_valuation_move_lines()
        move1_valuation_aml = valuation_aml[-1]
        self.assertEqual(move1_valuation_aml.debit, 0)
        self.assertEqual(move1_valuation_aml.credit, 400)
        output_aml = self._get_stock_output_move_lines()
        move1_output_aml = output_aml[-1]
        self.assertEqual(move1_output_aml.debit, 400)
        self.assertEqual(move1_output_aml.credit, 0)

        # ---------------------------------------------------------------------
        # Receive 40 units @ 15
        # ---------------------------------------------------------------------
        move2 = self.env['stock.move'].create({
            'name': '40 in @15',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 40.0,
            'price_unit': 15.0,
            'move_line_ids': [(0, 0, {
                'product_id': self.product1.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 40.0,
            })]
        })
        move2._action_confirm()
        move2._action_done()

        # stock values for move2
        self.assertEqual(move2.value, 600.0)
        self.assertEqual(move2.remaining_qty, 40.0)
        self.assertEqual(move2.price_unit, 15.0)
        self.assertEqual(move2.remaining_value, 600.0)

        # account values for move2
        valuation_aml = self._get_stock_valuation_move_lines()
        move2_valuation_aml = valuation_aml[-1]
        self.assertEqual(move2_valuation_aml.debit, 600)
        self.assertEqual(move2_valuation_aml.credit, 0)
        input_aml = self._get_stock_input_move_lines()
        move2_input_aml = input_aml[-1]
        self.assertEqual(move2_input_aml.debit, 0)
        self.assertEqual(move2_input_aml.credit, 600)

        # ---------------------------------------------------------------------
        # Run the vacuum
        # ---------------------------------------------------------------------
        self.env['stock.move']._run_fifo_vacuum()

        # stock values for move1 and move2
        self.assertEqual(move1.value, -400.0)
        self.assertEqual(move1.remaining_value, 200.0)
        self.assertEqual(move1.remaining_qty, -10.0)
        self.assertEqual(move2.value, 600.0)
        self.assertEqual(move2.remaining_value, 0.0)
        self.assertEqual(move2.remaining_qty, 0.0)

        # account values after vacuum
        valuation_aml = self._get_stock_valuation_move_lines()
        vacuum1_valuation_aml = valuation_aml[-1]
        self.assertEqual(vacuum1_valuation_aml.debit, 0)
        # 200 was credited more in valuation (we initially credited 400 but the vacuum realized
        # that 600 was the right value)
        self.assertEqual(vacuum1_valuation_aml.credit, 200)
        output_aml = self._get_stock_output_move_lines()
        vacuum1_output_aml = output_aml[-1]
        # 200 was debited more in output (we initially debited 400 but the vacuum realized
        # that 600 was the right value)
        self.assertEqual(vacuum1_output_aml.debit, 200)
        self.assertEqual(vacuum1_output_aml.credit, 0)

        self.assertTrue(set(move1.mapped('account_move_ids.line_ids').ids) == {move1_valuation_aml.id, move1_output_aml.id, vacuum1_valuation_aml.id, vacuum1_output_aml.id})

        # ---------------------------------------------------------------------
        # Receive 20 units @ 25
        # ---------------------------------------------------------------------
        move3 = self.env['stock.move'].create({
            'name': '20 in @25',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 20.0,
            'price_unit': 25.0,
            'move_line_ids': [(0, 0, {
                'product_id': self.product1.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 20.0
            })]
        })
        move3._action_confirm()
        move3._action_done()

        # stock values for move3
        self.assertEqual(move3.value, 500.0)
        self.assertEqual(move3.remaining_value, 500.0)
        self.assertEqual(move3.remaining_qty, 20.0)

        # account values for move3
        valuation_aml = self._get_stock_valuation_move_lines()
        move3_valuation_aml = valuation_aml[-1]
        self.assertEqual(move3_valuation_aml.debit, 500)
        self.assertEqual(move3_valuation_aml.credit, 0)
        input_aml = self._get_stock_input_move_lines()
        move3_input_aml = input_aml[-1]
        self.assertEqual(move3_input_aml.debit, 0)
        self.assertEqual(move3_input_aml.credit, 500)

        # ---------------------------------------------------------------------
        # Run the vacuum
        # ---------------------------------------------------------------------
        self.env['stock.move']._run_fifo_vacuum()

        # stock values for move1-3
        self.assertEqual(move1.value, -400.0)
        self.assertEqual(move1.remaining_value, 0.0)
        self.assertEqual(move1.remaining_qty, 0.0)
        self.assertEqual(move2.value, 600.0)
        self.assertEqual(move2.remaining_value, 0.0)
        self.assertEqual(move2.remaining_qty, 0.0)
        self.assertEqual(move3.value, 500.0)
        self.assertEqual(move3.remaining_value, 250.0)
        self.assertEqual(move3.remaining_qty, 10.0)

        # account values after vacuum
        valuation_aml = self._get_stock_valuation_move_lines()
        vacuum2_valuation_aml = valuation_aml[-1]
        self.assertEqual(vacuum2_valuation_aml.debit, 0)
        # 250 was credited more in valuation (we initially credited 400+200 but the vacuum realized
        # that 850 was the right value)
        self.assertEqual(vacuum2_valuation_aml.credit, 250)
        output_aml = self._get_stock_output_move_lines()
        vacuum2_output_aml = output_aml[-1]
        # 250 was debited more in output (we initially debited 400+200 but the vacuum realized
        # that 850 was the right value)
        self.assertEqual(vacuum2_output_aml.debit, 250)
        self.assertEqual(vacuum2_output_aml.credit, 0)

        self.assertTrue(set(move1.mapped('account_move_ids.line_ids').ids) == {move1_valuation_aml.id, move1_output_aml.id, vacuum1_valuation_aml.id, vacuum1_output_aml.id, vacuum2_valuation_aml.id, vacuum2_output_aml.id})

        # ---------------------------------------------------------------------
        # Ending
        # ---------------------------------------------------------------------
        self.assertEqual(self.product1.qty_available, 10)
        self.assertEqual(self.product1.stock_value, 250)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('debit')), 0)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('credit')), 1100)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 1100)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 850)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('debit')), 850)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('credit')), 0)

    def test_fifo_negative_2(self):
        """ Receives 10 units, send more, the extra quantity should be valued at the last fifo
        price, running the vacuum should not do anything.
        """
        self.product1.product_tmpl_id.cost_method = 'fifo'

        # ---------------------------------------------------------------------
        # Receive 10@10
        # ---------------------------------------------------------------------
        move1 = self.env['stock.move'].create({
            'name': '10 in',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10,
            'move_line_ids': [(0, 0, {
                'product_id': self.product1.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 10.0,
            })]
        })
        move1._action_confirm()
        move1._action_done()

        # stock values for move1
        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_qty, 10.0)
        self.assertEqual(move1.price_unit, 10.0)
        self.assertEqual(move1.remaining_value, 100.0)

        # account values for move1
        valuation_aml = self._get_stock_valuation_move_lines()
        move1_valuation_aml = valuation_aml[-1]
        self.assertEqual(move1_valuation_aml.debit, 100)
        self.assertEqual(move1_valuation_aml.credit, 0)
        input_aml = self._get_stock_input_move_lines()
        move1_input_aml = input_aml[-1]
        self.assertEqual(move1_input_aml.debit, 0)
        self.assertEqual(move1_input_aml.credit, 100)

        self.assertEqual(len(move1.account_move_ids), 1)

        # ---------------------------------------------------------------------
        # Send 12
        # ---------------------------------------------------------------------
        move2 = self.env['stock.move'].create({
            'name': '12 out (2 negative)',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 12.0,
            'price_unit': 0,
            'move_line_ids': [(0, 0, {
                'product_id': self.product1.id,
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 12.0,
            })]
        })
        move2._action_confirm()
        move2._action_done()

        # stock values for move2
        self.assertEqual(move2.value, -120.0)
        self.assertEqual(move2.remaining_qty, -2.0)
        self.assertEqual(move2.remaining_value, -20.0)

        # account values for move2
        valuation_aml = self._get_stock_valuation_move_lines()
        move2_valuation_aml = valuation_aml[-1]
        self.assertEqual(move2_valuation_aml.debit, 0)
        self.assertEqual(move2_valuation_aml.credit, 120)
        output_aml = self._get_stock_output_move_lines()
        move2_output_aml = output_aml[-1]
        self.assertEqual(move2_output_aml.debit, 120)
        self.assertEqual(move2_output_aml.credit, 0)

        self.assertEqual(len(move2.account_move_ids), 1)

        # ---------------------------------------------------------------------
        # Run the vacuum
        # ---------------------------------------------------------------------
        self.env['stock.move']._run_fifo_vacuum()

        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_qty, 0.0)
        self.assertEqual(move1.price_unit, 10.0)
        self.assertEqual(move1.remaining_value, 0.0)
        self.assertEqual(move2.value, -120.0)
        self.assertEqual(move2.remaining_qty, -2.0)
        self.assertEqual(move2.remaining_value, -20.0)

        self.assertEqual(len(move1.account_move_ids), 1)
        self.assertEqual(len(move2.account_move_ids), 1)

        # ---------------------------------------------------------------------
        # Ending
        # ---------------------------------------------------------------------
        self.assertEqual(self.product1.qty_available, -2)
        self.assertEqual(self.product1.stock_value, -20)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('debit')), 0)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('credit')), 100)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 100)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 120)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('debit')), 120)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('credit')), 0)

    def test_fifo_negative_3(self):
        """ Receives 10 units, send 10 units, then send more: the extra quantity should be valued
        at the last fifo price, running the vacuum should not do anything.
        """
        self.product1.product_tmpl_id.cost_method = 'fifo'

        # ---------------------------------------------------------------------
        # Receive 10@10
        # ---------------------------------------------------------------------
        move1 = self.env['stock.move'].create({
            'name': '10 in',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10,
            'move_line_ids': [(0, 0, {
                'product_id': self.product1.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 10.0,
            })]
        })
        move1._action_confirm()
        move1._action_done()

        # stock values for move1
        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_qty, 10.0)
        self.assertEqual(move1.price_unit, 10.0)
        self.assertEqual(move1.remaining_value, 100.0)

        # account values for move1
        valuation_aml = self._get_stock_valuation_move_lines()
        move1_valuation_aml = valuation_aml[-1]
        self.assertEqual(move1_valuation_aml.debit, 100)
        self.assertEqual(move1_valuation_aml.credit, 0)
        input_aml = self._get_stock_input_move_lines()
        move1_input_aml = input_aml[-1]
        self.assertEqual(move1_input_aml.debit, 0)
        self.assertEqual(move1_input_aml.credit, 100)

        self.assertEqual(len(move1.account_move_ids), 1)

        # ---------------------------------------------------------------------
        # Send 10
        # ---------------------------------------------------------------------
        move2 = self.env['stock.move'].create({
            'name': '10 out',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'move_line_ids': [(0, 0, {
                'product_id': self.product1.id,
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 10.0,
            })]
        })
        move2._action_confirm()
        move2._action_done()

        # stock values for move2
        self.assertEqual(move2.value, -100.0)
        self.assertEqual(move2.remaining_qty, 0.0)
        self.assertEqual(move2.remaining_value, 0.0)

        # account values for move2
        valuation_aml = self._get_stock_valuation_move_lines()
        move2_valuation_aml = valuation_aml[-1]
        self.assertEqual(move2_valuation_aml.debit, 0)
        self.assertEqual(move2_valuation_aml.credit, 100)
        output_aml = self._get_stock_output_move_lines()
        move2_output_aml = output_aml[-1]
        self.assertEqual(move2_output_aml.debit, 100)
        self.assertEqual(move2_output_aml.credit, 0)

        self.assertEqual(len(move2.account_move_ids), 1)

        # ---------------------------------------------------------------------
        # Send 21
        # ---------------------------------------------------------------------
        move3 = self.env['stock.move'].create({
            'name': '10 in',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 21.0,
            'price_unit': 0,
            'move_line_ids': [(0, 0, {
                'product_id': self.product1.id,
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 21.0,
            })]
        })
        move3._action_confirm()
        move3._action_done()

        # stock values for move3
        self.assertEqual(move3.value, -210.0)
        self.assertEqual(move3.remaining_qty, -21.0)
        self.assertEqual(move3.remaining_value, -210.0)

        # account values for move3
        valuation_aml = self._get_stock_valuation_move_lines()
        move3_valuation_aml = valuation_aml[-1]
        self.assertEqual(move3_valuation_aml.debit, 0)
        self.assertEqual(move3_valuation_aml.credit, 210)
        output_aml = self._get_stock_output_move_lines()
        move3_output_aml = output_aml[-1]
        self.assertEqual(move3_output_aml.debit, 210)
        self.assertEqual(move3_output_aml.credit, 0)

        self.assertEqual(len(move3.account_move_ids), 1)

        # ---------------------------------------------------------------------
        # Run the vacuum
        # ---------------------------------------------------------------------
        self.env['stock.move']._run_fifo_vacuum()
        self.assertEqual(len(move3.account_move_ids), 1)

        # the vacuum shouldn't do anything in this case
        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_qty, 0.0)
        self.assertEqual(move1.price_unit, 10.0)
        self.assertEqual(move1.remaining_value, 0.0)
        self.assertEqual(move2.value, -100.0)
        self.assertEqual(move2.remaining_qty, 0.0)
        self.assertEqual(move2.remaining_value, 0.0)
        self.assertEqual(move3.value, -210.0)
        self.assertEqual(move3.remaining_qty, -21.0)
        self.assertEqual(move3.remaining_value, -210.0)

        self.assertEqual(len(move1.account_move_ids), 1)
        self.assertEqual(len(move2.account_move_ids), 1)
        self.assertEqual(len(move3.account_move_ids), 1)

        # ---------------------------------------------------------------------
        # Ending
        # ---------------------------------------------------------------------
        self.assertEqual(self.product1.qty_available, -21)
        self.assertEqual(self.product1.stock_value, -210)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('debit')), 0)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('credit')), 100)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 100)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 310)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('debit')), 310)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('credit')), 0)

    def test_fifo_add_move_in_done_picking_1(self):
        self.product1.product_tmpl_id.cost_method = 'fifo'

        # ---------------------------------------------------------------------
        # Receive 10@10
        # ---------------------------------------------------------------------
        receipt = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'partner_id': self.partner.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })

        move1 = self.env['stock.move'].create({
            'picking_id': receipt.id,
            'name': '10 in',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10,
            'move_line_ids': [(0, 0, {
                'product_id': self.product1.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 10.0,
            })]
        })
        move1._action_confirm()
        move1._action_done()

        # stock values for move1
        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_qty, 10.0)
        self.assertEqual(move1.price_unit, 10.0)
        self.assertEqual(move1.remaining_value, 100.0)

        # ---------------------------------------------------------------------
        # Add a stock move, receive 10@20 of another product
        # ---------------------------------------------------------------------
        self.product2.product_tmpl_id.cost_method = 'fifo'
        self.product2.standard_price = 20
        move2 = self.env['stock.move'].create({
            'picking_id': receipt.id,
            'name': '10 in',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'state': 'done',  # simulate default_get override
            'move_line_ids': [(0, 0, {
                'product_id': self.product2.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 10.0,
            })]
        })
        self.assertEqual(move2.value, 200.0)
        self.assertEqual(move2.remaining_qty, 10.0)
        self.assertEqual(move2.price_unit, 20.0)
        self.assertEqual(move2.remaining_value, 200.0)

        self.assertEqual(self.product1.qty_available, 10)
        self.assertEqual(self.product1.stock_value, 100)
        self.assertEqual(self.product2.qty_available, 10)
        self.assertEqual(self.product2.stock_value, 200)

        # ---------------------------------------------------------------------
        # Edit the previous stock move, receive 11
        # ---------------------------------------------------------------------
        move2.quantity_done = 11

        self.assertEqual(move2.value, 200.0)
        self.assertEqual(move2.remaining_qty, 11.0)
        self.assertEqual(move2.price_unit, 20.0)
        self.assertEqual(move2.remaining_value, 220.0)

        # ---------------------------------------------------------------------
        # Send 11 product 2
        # ---------------------------------------------------------------------
        delivery = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'partner_id': self.partner.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
        })
        move3 = self.env['stock.move'].create({
            'picking_id': delivery.id,
            'name': '11 out',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 11.0,
            'move_line_ids': [(0, 0, {
                'product_id': self.product2.id,
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 11.0,
            })]
        })

        move3._action_confirm()
        move3._action_done()

        self.assertEqual(move3.value, -220.0)
        self.assertEqual(move3.remaining_qty, 0.0)
        self.assertEqual(move3.price_unit, -20.0)
        self.assertEqual(move3.remaining_value, 0.0)

        # ---------------------------------------------------------------------
        # Add one move of product 2
        # ---------------------------------------------------------------------
        move4 = self.env['stock.move'].create({
            'picking_id': delivery.id,
            'name': '1 out',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'state': 'done',  # simulate default_get override
            'move_line_ids': [(0, 0, {
                'product_id': self.product2.id,
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 1.0,
            })]
        })
        self.assertEqual(move4.value, -20.0)
        self.assertEqual(move4.remaining_qty, -1.0)
        self.assertEqual(move4.price_unit, -20.0)
        self.assertEqual(move4.remaining_value, -20.0)

        # ---------------------------------------------------------------------
        # edit the created move, add 1
        # ---------------------------------------------------------------------
        move4.quantity_done = 2

        self.assertEqual(move4.value, -20.0)
        self.assertEqual(move4.remaining_qty, -2.0)
        self.assertEqual(move4.price_unit, -20.0)
        self.assertEqual(move4.remaining_value, -40.0)

        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('debit')), 0)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('credit')), 320) # 10*10 + 11*20
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 320)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 260)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('debit')), 260)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('credit')), 0)

        self.env['stock.move']._run_fifo_vacuum()

        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('debit')), 0)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('credit')), 320) # 10*10 + 11*20
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 320)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 260)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('debit')), 260)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('credit')), 0)

        # ---------------------------------------------------------------------
        # receive 2 products 2 @ 30
        # ---------------------------------------------------------------------
        move1 = self.env['stock.move'].create({
            'picking_id': receipt.id,
            'name': '10 in',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
            'price_unit': 30,
            'move_line_ids': [(0, 0, {
                'product_id': self.product2.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 2.0,
            })]
        })
        move1._action_confirm()
        move1._action_done()

        # ---------------------------------------------------------------------
        # run vacuum
        # ---------------------------------------------------------------------
        self.env['stock.move']._run_fifo_vacuum()

        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('debit')), 0)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('credit')), 380) # 10*10 + 11*20
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 380)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 280) # 260/
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('debit')), 280)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('credit')), 0)

        self.assertEqual(self.product2.qty_available, 0)
        self.assertEqual(self.product2.stock_value, 0)
        self.assertEqual(move4.remaining_value, 0)

    def test_fifo_add_moveline_in_done_move_1(self):
        self.product1.product_tmpl_id.cost_method = 'fifo'

        # ---------------------------------------------------------------------
        # Receive 10@10
        # ---------------------------------------------------------------------
        move1 = self.env['stock.move'].create({
            'name': '10 in',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10,
            'move_line_ids': [(0, 0, {
                'product_id': self.product1.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 10.0,
            })]
        })
        move1._action_confirm()
        move1._action_done()

        # stock values for move1
        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_qty, 10.0)
        self.assertEqual(move1.price_unit, 10.0)
        self.assertEqual(move1.remaining_value, 100.0)

        self.assertEqual(len(move1.account_move_ids), 1)

        # ---------------------------------------------------------------------
        # Add a new move line to receive 10 more
        # ---------------------------------------------------------------------
        self.assertEqual(len(move1.move_line_ids), 1)
        self.env['stock.move.line'].with_context(debug=True).create({
            'move_id': move1.id,
            'product_id': move1.product_id.id,
            'qty_done': 10,
            'product_uom_id': move1.product_uom.id,
            'location_id': move1.location_id.id,
            'location_dest_id': move1.location_dest_id.id,
        })
        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_qty, 20.0)
        self.assertEqual(move1.price_unit, 10.0)
        self.assertEqual(move1.remaining_value, 200.0)

        self.assertEqual(len(move1.account_move_ids), 2)

        self.assertEqual(self.product1.qty_available, 20)
        self.assertEqual(self.product1.stock_value, 200)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('debit')), 0)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('credit')), 200)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 200)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 0)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('debit')), 0)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('credit')), 0)

    def test_fifo_edit_done_move1(self):
        """ Check that incrementing the done quantity will correctly re-run a fifo lookup.
        """
        self.product1.product_tmpl_id.cost_method = 'fifo'

        # ---------------------------------------------------------------------
        # Receive 10@10
        # ---------------------------------------------------------------------
        move1 = self.env['stock.move'].create({
            'name': 'receive 10@10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10,
            'move_line_ids': [(0, 0, {
                'product_id': self.product1.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 10.0,
            })]
        })
        move1._action_confirm()
        move1._action_done()

        # stock values for move1
        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_qty, 10.0)
        self.assertEqual(move1.price_unit, 10.0)
        self.assertEqual(move1.remaining_value, 100.0)

        # account values for move1
        valuation_aml = self._get_stock_valuation_move_lines()
        move1_valuation_aml = valuation_aml[-1]
        self.assertEqual(move1_valuation_aml.debit, 100)
        self.assertEqual(move1_valuation_aml.credit, 0)
        input_aml = self._get_stock_input_move_lines()
        move1_input_aml = input_aml[-1]
        self.assertEqual(move1_input_aml.debit, 0)
        self.assertEqual(move1_input_aml.credit, 100)

        self.assertEqual(len(move1.account_move_ids), 1)

        self.assertEqual(self.product1.stock_value, 100)

        # ---------------------------------------------------------------------
        # Receive 10@12
        # ---------------------------------------------------------------------
        move2 = self.env['stock.move'].create({
            'name': 'receive 10@12',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 12,
            'move_line_ids': [(0, 0, {
                'product_id': self.product1.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 10.0,
            })]
        })
        move2._action_confirm()
        move2._action_done()

        # stock values for move2
        self.assertEqual(move2.value, 120.0)
        self.assertEqual(move2.remaining_qty, 10.0)
        self.assertEqual(move2.price_unit, 12.0)
        self.assertEqual(move2.remaining_value, 120.0)

        # account values for move2
        valuation_aml = self._get_stock_valuation_move_lines()
        move2_valuation_aml = valuation_aml[-1]
        self.assertEqual(move2_valuation_aml.debit, 120)
        self.assertEqual(move2_valuation_aml.credit, 0)
        input_aml = self._get_stock_input_move_lines()
        move2_input_aml = input_aml[-1]
        self.assertEqual(move2_input_aml.debit, 0)
        self.assertEqual(move2_input_aml.credit, 120)

        self.assertEqual(len(move2.account_move_ids), 1)

        self.assertEqual(self.product1.stock_value, 220)

        # ---------------------------------------------------------------------
        # Send 8
        # ---------------------------------------------------------------------
        move3 = self.env['stock.move'].create({
            'name': '12 out (2 negative)',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 8.0,
            'price_unit': 0,
            'move_line_ids': [(0, 0, {
                'product_id': self.product1.id,
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 8.0,
            })]
        })
        move3._action_confirm()
        move3._action_done()

        # stock values for move3
        self.assertEqual(move3.value, -80.0)
        self.assertEqual(move3.remaining_qty, 0.0)
        self.assertEqual(move3.remaining_value, 0.0)

        # older move
        self.assertEqual(move1.remaining_value, 20)
        self.assertEqual(move2.remaining_value, 120)

        # account values for move3
        valuation_aml = self._get_stock_valuation_move_lines()
        move3_valuation_aml = valuation_aml[-1]
        self.assertEqual(move3_valuation_aml.debit, 0)
        output_aml = self._get_stock_output_move_lines()
        move3_output_aml = output_aml[-1]
        self.assertEqual(move3_output_aml.debit, 80)
        self.assertEqual(move3_output_aml.credit, 0)

        self.assertEqual(len(move3.account_move_ids), 1)

        self.assertEqual(self.product1.stock_value, 140)

        # ---------------------------------------------------------------------
        # Edit last move, send 14 instead
        # it should send 2@10 and 4@12
        # ---------------------------------------------------------------------
        move3.quantity_done = 14
        self.assertEqual(move3.product_qty, 14)

        # older move
        self.assertEqual(move1.remaining_value, 0)  # before, 20
        self.assertEqual(move2.remaining_value, 72)  # before, 120

        # account values for move3
        valuation_aml = self._get_stock_valuation_move_lines()
        move3_valuation_aml = valuation_aml[-1]
        self.assertEqual(move3_valuation_aml.debit, 0)
        output_aml = self._get_stock_output_move_lines()
        move3_output_aml = output_aml[-1]
        self.assertEqual(move3_output_aml.debit, 68)
        self.assertEqual(move3_output_aml.credit, 0)

        self.assertEqual(len(move3.account_move_ids), 2)

        self.assertEqual(self.product1.stock_value, 72)

        # ---------------------------------------------------------------------
        # Ending
        # ---------------------------------------------------------------------
        self.assertEqual(self.product1.qty_available, 6)
        self.assertEqual(self.product1.stock_value, 72)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('debit')), 0)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('credit')), 220)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 220)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 148)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('debit')), 148)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('credit')), 0)

    def test_fifo_edit_done_move2(self):
        self.product1.product_tmpl_id.cost_method = 'fifo'

        # ---------------------------------------------------------------------
        # Receive 10@10
        # ---------------------------------------------------------------------
        move1 = self.env['stock.move'].create({
            'name': 'receive 10@10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10,
            'move_line_ids': [(0, 0, {
                'product_id': self.product1.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 10.0,
            })]
        })
        move1._action_confirm()
        move1._action_done()

        # stock values for move1
        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_qty, 10.0)
        self.assertEqual(move1.price_unit, 10.0)
        self.assertEqual(move1.remaining_value, 100.0)

        # ---------------------------------------------------------------------
        # Send 10
        # ---------------------------------------------------------------------
        move2 = self.env['stock.move'].create({
            'name': '12 out (2 negative)',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 0,
            'move_line_ids': [(0, 0, {
                'product_id': self.product1.id,
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 10.0,
            })]
        })
        move2._action_confirm()
        move2._action_done()

        # stock values for move2
        self.assertEqual(move2.value, -100.0)
        self.assertEqual(move2.remaining_qty, 0.0)
        self.assertEqual(move2.remaining_value, 0.0)

        # ---------------------------------------------------------------------
        # Actually, send 8 in the last move
        # ---------------------------------------------------------------------
        move2.quantity_done = 8

        self.assertEqual(move2.value, -100.0)
        self.assertEqual(move2.remaining_qty, 0.0)
        self.assertEqual(move2.remaining_value, 0.0)

        self.assertEqual(move1.remaining_qty, 2.0)
        self.assertEqual(move1.remaining_value, 20.0)

        self.product1.qty_available = 2
        self.product1.stock_value = 20

        # ---------------------------------------------------------------------
        # Actually, send 10 in the last move
        # ---------------------------------------------------------------------
        move2.with_context(debug=True).quantity_done = 10

        self.assertEqual(move2.value, -100.0)
        self.assertEqual(move2.remaining_qty, 0.0)
        self.assertEqual(move2.remaining_value, 0.0)

        self.assertEqual(move1.remaining_qty, 0.0)
        self.assertEqual(move1.remaining_value, 0.0)

        self.product1.qty_available = 2
        self.product1.stock_value = 20

    def test_average_perpetual_1(self):
        # http://accountingexplained.com/financial/inventories/avco-method
        self.product1.product_tmpl_id.cost_method = 'average'

        # Beginning Inventory: 60 units @ 15.00 per unit
        move1 = self.env['stock.move'].create({
            'name': '60 units @ 15.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 60.0,
            'price_unit': 15,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 60.0
        move1._action_done()

        self.assertEqual(move1.value, 900.0)

        # Purchase 140 units @ 15.50 per unit
        move2 = self.env['stock.move'].create({
            'name': '140 units @ 15.50 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 140.0,
            'price_unit': 15.50,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 140.0
        move2._action_done()

        self.assertEqual(move2.value, 2170.0)

        # Sale 190 units @ 15.35 per unit
        move3 = self.env['stock.move'].create({
            'name': 'Sale 190 units @ 19.00 per unit',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 190.0,
        })
        move3._action_confirm()
        move3._action_assign()
        move3.move_line_ids.qty_done = 190.0
        move3._action_done()


        self.assertEqual(move3.value, -2916.5)

        # Purchase 70 units @ $16.00 per unit
        move4 = self.env['stock.move'].create({
            'name': '70 units @ $16.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 70.0,
            'price_unit': 16.00,
        })
        move4._action_confirm()
        move4._action_assign()
        move4.move_line_ids.qty_done = 70.0
        move4._action_done()

        self.assertEqual(move4.value, 1120.0)

        # Sale 30 units @ $19.50 per unit
        move5 = self.env['stock.move'].create({
            'name': '30 units @ $19.50 per unit',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 30.0,
        })
        move5._action_confirm()
        move5._action_assign()
        move5.move_line_ids.qty_done = 30.0
        move5._action_done()

        self.assertEqual(move5.value, -477.6)

        # Receives 10 units but assign them to an owner, the valuation should not be impacted.
        move6 = self.env['stock.move'].create({
            'name': '10 units to an owner',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 99,
        })
        move6._action_confirm()
        move6._action_assign()
        move6.move_line_ids.owner_id = self.owner1.id
        move6.move_line_ids.qty_done = 10.0
        move6._action_done()

        self.assertEqual(move6.value, 0)

    def test_average_perpetual_2(self):
        self.product1.product_tmpl_id.cost_method = 'average'

        move1 = self.env['stock.move'].create({
            'name': 'Receive 10 units at 10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10.0
        move1._action_done()

        move2 = self.env['stock.move'].create({
            'name': 'Receive 10 units at 15',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 15,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 10.0
        move2._action_done()

        move3 = self.env['stock.move'].create({
            'name': 'Deliver 15 units',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 15.0,
        })
        move3._action_confirm()
        move3._action_assign()
        move3.move_line_ids.qty_done = 15.0
        move3._action_done()

        move4 = self.env['stock.move'].create({
            'name': 'Deliver 10 units',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move4._action_confirm()
        move4._action_assign()
        move4.move_line_ids.qty_done = 10.0
        move4._action_done()

        move2.move_line_ids.qty_done = 20

        self.assertEqual(self.product1.stock_value, 87.5)

    def test_average_perpetual_3(self):
        self.product1.product_tmpl_id.cost_method = 'average'

        move1 = self.env['stock.move'].create({
            'name': 'Receive  10 units at 10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10.0
        move1._action_done()

        move2 = self.env['stock.move'].create({
            'name': 'Receive 10 units at 15',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 15,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 10.0
        move2._action_done()

        move3 = self.env['stock.move'].create({
            'name': 'Deliver 15 units',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 15.0,
        })
        move3._action_confirm()
        move3._action_assign()
        move3.move_line_ids.qty_done = 15.0
        move3._action_done()

        move4 = self.env['stock.move'].create({
            'name': 'Deliver 10 units',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move4._action_confirm()
        move4._action_assign()
        move4.move_line_ids.qty_done = 10.0
        move4._action_done()
        move2.move_line_ids.qty_done = 0
        self.assertEqual(self.product1.stock_value, -187.5)

    def test_average_negative_1(self):
        """ Test edit in the past. Receive 10, send 20, edit the second move to only send 10.
        """
        self.product1.product_tmpl_id.cost_method = 'average'

        move1 = self.env['stock.move'].create({
            'name': 'Receive 10 units at 10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10.0
        move1._action_done()

        move2 = self.env['stock.move'].create({
            'name': 'send 20 units',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 20.0,
        })
        move2._action_confirm()
        move2._action_assign()
        move2._force_assign()
        move2.move_line_ids.qty_done = 20.0
        move2._action_done()

        valuation_aml = self._get_stock_valuation_move_lines()
        move2_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 2)
        self.assertEqual(move2_valuation_aml.debit, 0)
        self.assertEqual(move2_valuation_aml.credit, 200)

        move2.quantity_done = 10.0

        valuation_aml = self._get_stock_valuation_move_lines()
        move2_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 3)
        self.assertEqual(move2_valuation_aml.debit, 100)
        self.assertEqual(move2_valuation_aml.credit, 0)

        move2.quantity_done = 11.0

        valuation_aml = self._get_stock_valuation_move_lines()
        move2_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 4)
        self.assertEqual(move2_valuation_aml.debit, 0)
        self.assertEqual(move2_valuation_aml.credit, 10)

    def test_average_negative_2(self):
        """ Send goods that you don't have in stock and never received any unit.
        """
        self.product1.product_tmpl_id.cost_method = 'average'

        # set a standard price
        self.product1.standard_price = 99

        # send 10 units that we do not have
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0)
        move1 = self.env['stock.move'].create({
            'name': 'test_average_negative_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move1._action_confirm()
        move1._force_assign()
        move1.quantity_done = 10.0
        move1._action_done()
        self.assertEqual(move1.value, -990.0)  # as no move out were done for this product, fallback on the standard price

    def test_average_negative_3(self):
        """ Send goods that you don't have in stock but received and send some units before.
        """
        self.product1.product_tmpl_id.cost_method = 'average'

        # set a standard price
        self.product1.standard_price = 99

        # Receives 10 produts at 10
        move1 = self.env['stock.move'].create({
            'name': '68 units @ 15.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10.0
        move1._action_done()

        self.assertEqual(move1.value, 100.0)

        # send 10 products
        move2 = self.env['stock.move'].create({
            'name': 'Sale 94 units @ 19.00 per unit',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 10.0
        move2._action_done()

        self.assertEqual(move2.value, -100.0)
        self.assertEqual(move2.remaining_qty, 0.0)  # unused in average move

        # send 10 products again
        move3 = self.env['stock.move'].create({
            'name': 'Sale 94 units @ 19.00 per unit',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move3._action_confirm()
        move3._force_assign()
        move3.quantity_done = 10.0
        move3._action_done()

        self.assertEqual(move3.value, -100.0)  # as no move out were done for this product, fallback on latest cost

    def test_average_negative_4(self):
        self.product1.product_tmpl_id.cost_method = 'average'

        # set a standard price
        self.product1.standard_price = 99

        # Receives 10 produts at 10
        move1 = self.env['stock.move'].create({
            'name': '68 units @ 15.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10.0
        move1._action_done()

        self.assertEqual(move1.value, 100.0)

    def test_average_negative_5(self):
        self.product1.product_tmpl_id.cost_method = 'average'

        # in 10 @ 10
        move1 = self.env['stock.move'].create({
            'name': '10 units @ 10.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10.0
        move1._action_done()

        self.assertEqual(move1.value, 100.0)
        self.assertEqual(self.product1.standard_price, 10)

        # in 10 @ 20
        move2 = self.env['stock.move'].create({
            'name': '10 units @ 20.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 20,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 10.0
        move2._action_done()

        self.assertEqual(move2.value, 200.0)
        self.assertEqual(self.product1.standard_price, 15)

        # send 5
        move3 = self.env['stock.move'].create({
            'name': 'Sale 5 units',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })
        move3._action_confirm()
        move3._force_assign()
        move3.quantity_done = 5.0
        move3._action_done()

        self.assertEqual(move3.value, -75.0)
        self.assertEqual(self.product1.standard_price, 15)

        # send 30
        move4 = self.env['stock.move'].create({
            'name': 'Sale 5 units',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 30.0,
        })
        move4._action_confirm()
        move4._force_assign()
        move4.quantity_done = 30.0
        move4._action_done()

        self.assertEqual(move4.value, -450.0)
        self.assertEqual(self.product1.standard_price, 15)

        # in 20 @ 20
        move5 = self.env['stock.move'].create({
            'name': '20 units @ 20.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 20.0,
            'price_unit': 20,
        })
        move5._action_confirm()
        move5._action_assign()
        move5.move_line_ids.qty_done = 20.0
        move5._action_done()

        self.assertEqual(move5.value, 400.0)
        self.assertEqual(self.product1.standard_price, 35)

        self.assertEqual(self.product1.qty_available, 5)

        # send 5 products to empty the inventory, the average price should not go to 0
        move6 = self.env['stock.move'].create({
            'name': 'Sale 5 units',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })
        move6._action_confirm()
        move6._force_assign()
        move6.quantity_done = 5.0
        move6._action_done()

        self.assertEqual(move6.value, -175.0)
        self.assertEqual(self.product1.standard_price, 35)

        # in 10 @ 10, the new average price should be 10
        move7 = self.env['stock.move'].create({
            'name': '10 units @ 10.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10,
        })
        move7._action_confirm()
        move7._action_assign()
        move7.move_line_ids.qty_done = 10.0
        move7._action_done()

        self.assertEqual(move7.value, 100.0)
        self.assertEqual(self.product1.standard_price, 10)

    def test_change_cost_method_1(self):
        """ Change the cost method from FIFO to AVCO.
        """
        # ---------------------------------------------------------------------
        # Use FIFO, make some operations
        # ---------------------------------------------------------------------
        self.product1.product_tmpl_id.cost_method = 'fifo'

        # receive 10@10
        move1 = self.env['stock.move'].create({
            'name': '10 units @ 10.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10.0
        move1._action_done()

        # receive 10@15
        move2 = self.env['stock.move'].create({
            'name': '10 units @ 10.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 15,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 10.0
        move2._action_done()

        # sell 1
        move3 = self.env['stock.move'].create({
            'name': 'Sale 5 units',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move3._action_confirm()
        move3._action_assign()
        move3.move_line_ids.qty_done = 1.0
        move3._action_done()

        self.assertEqual(self.product1.stock_value, 240)

        # ---------------------------------------------------------------------
        # Change the production valuation to AVCO
        # ---------------------------------------------------------------------
        self.product1.product_tmpl_id.cost_method = 'average'

        # valuation should stay to ~240
        self.assertAlmostEqual(self.product1.stock_value, 240, delta=0.03)

        # no accounting entry should be created

        # the cost should now be 12,65
        # (9 * 10) + (15 * 10) / 19
        self.assertEqual(self.product1.standard_price, 12.63)

    def test_change_cost_method_2(self):
        """ Change the cost method from FIFO to standard.
        """
        # ---------------------------------------------------------------------
        # Use FIFO, make some operations
        # ---------------------------------------------------------------------
        self.product1.product_tmpl_id.cost_method = 'fifo'

        # receive 10@10
        move1 = self.env['stock.move'].create({
            'name': '10 units @ 10.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10.0
        move1._action_done()

        # receive 10@15
        move2 = self.env['stock.move'].create({
            'name': '10 units @ 10.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 15,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 10.0
        move2._action_done()

        # sell 1
        move3 = self.env['stock.move'].create({
            'name': 'Sale 5 units',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
        move3._action_confirm()
        move3._action_assign()
        move3.move_line_ids.qty_done = 1.0
        move3._action_done()

        self.assertEqual(self.product1.stock_value, 240)

        # ---------------------------------------------------------------------
        # Change the production valuation to AVCO
        # ---------------------------------------------------------------------
        self.product1.with_context(debug=True).product_tmpl_id.cost_method = 'standard'

        # valuation should stay to ~240
        self.assertAlmostEqual(self.product1.stock_value, 240, delta=0.03)

        # no accounting entry should be created

        # the cost should now be 12,65
        # (9 * 10) + (15 * 10) / 19
        self.assertEqual(self.product1.standard_price, 12.63)

    def test_fifo_sublocation_valuation_1(self):
        """ Set the main stock as a view location. Receive 2 units of a
        product, put 1 unit in an internal sublocation and the second
        one in a scrap sublocation. Only a single unit, the one in the
        internal sublocation, should be valued. Then, send these two
        quants to a customer, only the one in the internal location
        should be valued.
        """
        self.product1.product_tmpl_id.cost_method = 'fifo'

        view_location = self.env['stock.location'].create({'name': 'view', 'usage': 'view'})
        subloc1 = self.env['stock.location'].create({
            'name': 'internal',
            'usage': 'internal',
            'location_id': view_location.id,
        })
        # sane settings for a scrap location, company_id doesn't matter
        subloc2 = self.env['stock.location'].create({
            'name': 'scrap',
            'usage': 'inventory',
            'location_id': view_location.id,
            'scrap_location': True,
        })

        move1 = self.env['stock.move'].create({
            'name': '2 units @ 10.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()

        move1.write({'move_line_ids': [
            (0, None, {
                'product_id': self.product1.id,
                'qty_done': 1,
                'location_id': self.supplier_location.id,
                'location_dest_id': subloc1.id,
                'product_uom_id': self.uom_unit.id
            }),
            (0, None, {
                'product_id': self.product1.id,
                'qty_done': 1,
                'location_id': self.supplier_location.id,
                'location_dest_id': subloc2.id,
                'product_uom_id': self.uom_unit.id
            }),
        ]})

        move1._action_done()
        self.assertEqual(move1.value, 10)
        self.assertEqual(move1.remaining_value, 10)
        self.assertEqual(move1.remaining_qty, 1)
        self.assertEqual(self.product1.stock_value, 10)
        self.assertTrue(len(move1.account_move_ids), 1)

        move2 = self.env['stock.move'].create({
            'name': '2 units out',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        move2._action_confirm()
        move2._action_assign()

        move2.write({'move_line_ids': [
            (0, None, {
                'product_id': self.product1.id,
                'qty_done': 1,
                'location_id': subloc1.id,
                'location_dest_id': self.supplier_location.id,
                'product_uom_id': self.uom_unit.id
            }),
            (0, None, {
                'product_id': self.product1.id,
                'qty_done': 1,
                'location_id': subloc2.id,
                'location_dest_id': self.supplier_location.id,
                'product_uom_id': self.uom_unit.id
            }),
        ]})
        move2._action_done()
        self.assertEqual(move2.value, -10)

    def test_move_in_or_out(self):
        """ Test a few combination of move and their move lines and
        check their valuation. A valued move should be IN or OUT.
        Creating a move that is IN and OUT should be forbidden.
        """
        # an internal move should be considered as OUT if any of its move line
        # is moved in a scrap location
        scrap = self.env['stock.location'].create({
            'name': 'scrap',
            'usage': 'inventory',
            'location_id': self.stock_location.id,
            'scrap_location': True,
        })

        move1 = self.env['stock.move'].create({
            'name': 'internal but out move',
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.write({'move_line_ids': [
            (0, None, {
                'product_id': self.product1.id,
                'qty_done': 1,
                'location_id': self.stock_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_id': self.uom_unit.id
            }),
            (0, None, {
                'product_id': self.product1.id,
                'qty_done': 1,
                'location_id': self.stock_location.id,
                'location_dest_id': scrap.id,
                'product_uom_id': self.uom_unit.id
            }),
        ]})
        self.assertEqual(move1._is_out(), True)

        # a move should be considered as invalid if some of its move lines are
        # entering the company and some are leaving
        customer1 = self.env['stock.location'].create({
            'name': 'customer',
            'usage': 'customer',
            'location_id': self.stock_location.id,
        })
        supplier1 = self.env['stock.location'].create({
            'name': 'supplier',
            'usage': 'supplier',
            'location_id': self.stock_location.id,
        })
        move2 = self.env['stock.move'].create({
            'name': 'internal but in and out move',
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.write({'move_line_ids': [
            (0, None, {
                'product_id': self.product1.id,
                'qty_done': 1,
                'location_id': customer1.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_id': self.uom_unit.id
            }),
            (0, None, {
                'product_id': self.product1.id,
                'qty_done': 1,
                'location_id': self.stock_location.id,
                'location_dest_id': customer1.id,
                'product_uom_id': self.uom_unit.id
            }),
        ]})
        self.assertEqual(move2._is_in(), True)
        self.assertEqual(move2._is_out(), True)
        with self.assertRaises(UserError):
            move2._action_done()

