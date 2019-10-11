# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo.exceptions import UserError
from odoo.fields import Datetime
from odoo.tests.common import Form, SavepointCase


def _create_accounting_data(env):
    """Create the accounts and journals used in stock valuation.

    :param env: environment used to create the records
    :return: an input account, an output account, a valuation account, an expense account, a stock journal
    """
    stock_input_account = env['account.account'].create({
        'name': 'Stock Input',
        'code': 'StockIn',
        'user_type_id': env.ref('account.data_account_type_current_assets').id,
        'reconcile': True,
    })
    stock_output_account = env['account.account'].create({
        'name': 'Stock Output',
        'code': 'StockOut',
        'user_type_id': env.ref('account.data_account_type_current_assets').id,
        'reconcile': True,
    })
    stock_valuation_account = env['account.account'].create({
        'name': 'Stock Valuation',
        'code': 'Stock Valuation',
        'user_type_id': env.ref('account.data_account_type_current_assets').id,
        'reconcile': True,
    })
    expense_account = env['account.account'].create({
        'name': 'Expense Account',
        'code': 'Expense Account',
        'user_type_id': env.ref('account.data_account_type_expenses').id,
        'reconcile': True,
    })
    stock_journal = env['account.journal'].create({
        'name': 'Stock Journal',
        'code': 'STJTEST',
        'type': 'general',
    })
    return stock_input_account, stock_output_account, stock_valuation_account, expense_account, stock_journal


class TestStockValuation(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestStockValuation, cls).setUpClass()
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')
        cls.partner = cls.env['res.partner'].create({'name': 'xxx'})
        cls.owner1 = cls.env['res.partner'].create({'name': 'owner1'})
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.product1 = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'default_code': 'prda',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.product2 = cls.env['product.product'].create({
            'name': 'Product B',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.inventory_user = cls.env['res.users'].create({
            'name': 'Pauline Poivraisselle',
            'login': 'pauline',
            'email': 'p.p@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [cls.env.ref('stock.group_stock_user').id])]
        })

        cls.stock_input_account, cls.stock_output_account, cls.stock_valuation_account, cls.expense_account, cls.stock_journal = _create_accounting_data(cls.env)
        cls.product1.categ_id.property_valuation = 'real_time'
        cls.product2.categ_id.property_valuation = 'real_time'
        cls.product1.write({
            'property_account_expense_id': cls.expense_account.id,
        })
        cls.product1.categ_id.write({
            'property_stock_account_input_categ_id': cls.stock_input_account.id,
            'property_stock_account_output_categ_id': cls.stock_output_account.id,
            'property_stock_valuation_account_id': cls.stock_valuation_account.id,
            'property_stock_journal': cls.stock_journal.id,
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

    def test_realtime(self):
        """ Stock moves update stock value with product x cost price,
        price change updates the stock value based on current stock level.
        """
        # Enter 10 products while price is 5.0
        self.product1._change_standard_price(5.0, self.expense_account.id)
        move1 = self.env['stock.move'].create({
            'name': 'IN 10 units @ 10.00 per unit',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10.0
        move1._action_done()

        # Set price to 6.0
        self.product1._change_standard_price(6.0, self.expense_account.id)
        stock_aml, price_change_aml = self._get_stock_valuation_move_lines()
        self.assertEqual(stock_aml.debit, 50)
        self.assertEqual(price_change_aml.debit, 10)
        self.assertEqual(price_change_aml.ref, 'prda')
        self.assertEqual(price_change_aml.product_id, self.product1)

    def test_fifo_perpetual_1(self):
        self.product1.categ_id.property_cost_method = 'fifo'

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
        self.assertEqual(move1.stock_valuation_layer_ids.unit_cost, 10.0)
        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 10.0)
        self.assertEqual(move1.stock_valuation_layer_ids.value, 100.0)

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
        self.assertEqual(move1_valuation_aml.product_id.id, self.product1.id)
        self.assertEqual(move1_valuation_aml.quantity, 10)
        self.assertEqual(move1_valuation_aml.product_uom_id.id, self.uom_unit.id)

        output_aml = self._get_stock_output_move_lines()
        self.assertEqual(len(output_aml), 0)

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
        self.assertEqual(move2.stock_valuation_layer_ids.unit_cost, 8.0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 10.0)
        self.assertEqual(move2.stock_valuation_layer_ids.value, 80.0)

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
        self.assertEqual(move2_valuation_aml.product_id.id, self.product1.id)
        self.assertEqual(move2_valuation_aml.quantity, 10)
        self.assertEqual(move2_valuation_aml.product_uom_id.id, self.uom_unit.id)

        output_aml = self._get_stock_output_move_lines()
        self.assertEqual(len(output_aml), 0)

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
        self.assertEqual(move3.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out move
        self.assertEqual(move3.stock_valuation_layer_ids.value, -30.0)  # took 3 items from move 1 @ 10.00 per unit

        # account values for move3
        input_aml = self._get_stock_input_move_lines()
        self.assertEqual(len(input_aml), 2)

        valuation_aml = self._get_stock_valuation_move_lines()
        move3_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 3)
        self.assertEqual(move3_valuation_aml.debit, 0)
        self.assertEqual(move3_valuation_aml.credit, 30)
        self.assertEqual(move3_valuation_aml.product_id.id, self.product1.id)
        # FIXME sle
        #self.assertEqual(move3_valuation_aml.quantity, -3)
        self.assertEqual(move3_valuation_aml.product_uom_id.id, self.uom_unit.id)

        output_aml = self._get_stock_output_move_lines()
        move3_output_aml = output_aml[-1]
        self.assertEqual(len(output_aml), 1)
        self.assertEqual(move3_output_aml.debit, 30)
        self.assertEqual(move3_output_aml.credit, 0)

        # ---------------------------------------------------------------------
        # Increase received quantity of move1 from 10 to 12, it should create
        # a new stock layer at the top of the queue.
        # ---------------------------------------------------------------------
        move1.quantity_done = 12

        # stock_account values for move3
        self.assertEqual(move1.stock_valuation_layer_ids.sorted()[-1].unit_cost, 10.0)
        self.assertEqual(sum(move1.stock_valuation_layer_ids.mapped('remaining_qty')), 9.0)
        self.assertEqual(sum(move1.stock_valuation_layer_ids.mapped('value')), 120.0)  # move 1 is now 10@10 + 2@10

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
        self.assertEqual(move1_correction_valuation_aml.product_id.id, self.product1.id)
        self.assertEqual(move1_correction_valuation_aml.quantity, 2)
        self.assertEqual(move1_correction_valuation_aml.product_uom_id.id, self.uom_unit.id)

        output_aml = self._get_stock_output_move_lines()
        self.assertEqual(len(output_aml), 1)

        # ---------------------------------------------------------------------
        # Sale 9 units, the units available from the previous increase are not sent
        # immediately as the new layer is at the top of the queue.
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
        self.assertEqual(move4.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out move
        self.assertEqual(move4.stock_valuation_layer_ids.value, -86.0)  # took 9 items from move 1 @ 10.00 per unit

        # account values for move4
        input_aml = self._get_stock_input_move_lines()
        self.assertEqual(len(input_aml), 3)

        valuation_aml = self._get_stock_valuation_move_lines()
        move4_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 5)
        self.assertEqual(move4_valuation_aml.debit, 0)
        self.assertEqual(move4_valuation_aml.credit, 86)
        self.assertEqual(move4_valuation_aml.product_id.id, self.product1.id)
        # FIXME sle
        #self.assertEqual(move4_valuation_aml.quantity, -9)
        self.assertEqual(move4_valuation_aml.product_uom_id.id, self.uom_unit.id)

        output_aml = self._get_stock_output_move_lines()
        move4_output_aml = output_aml[-1]
        self.assertEqual(len(output_aml), 2)
        self.assertEqual(move4_output_aml.debit, 86)
        self.assertEqual(move4_output_aml.credit, 0)

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
        # (took 8 from the second receipt and 2 from the increase of the first receipt)
        self.assertEqual(move5.stock_valuation_layer_ids.remaining_qty, -10.0)
        self.assertEqual(move5.stock_valuation_layer_ids.value, -184.0)

        # account values for move5
        input_aml = self._get_stock_input_move_lines()
        self.assertEqual(len(input_aml), 3)

        valuation_aml = self._get_stock_valuation_move_lines()
        move5_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 6)
        self.assertEqual(move5_valuation_aml.debit, 0)
        self.assertEqual(move5_valuation_aml.credit, 184)
        self.assertEqual(move5_valuation_aml.product_id.id, self.product1.id)
        #self.assertEqual(move5_valuation_aml.quantity, -20)
        self.assertEqual(move5_valuation_aml.product_uom_id.id, self.uom_unit.id)

        output_aml = self._get_stock_output_move_lines()
        move5_output_aml = output_aml[-1]
        self.assertEqual(len(output_aml), 3)
        self.assertEqual(move5_output_aml.debit, 184)
        self.assertEqual(move5_output_aml.credit, 0)

        # ---------------------------------------------------------------------
        # Receive 10 units @ 12.00 to counterbalance the negative, the vacuum
        # will be called directly: 10@10 should be revalued 10@12
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
        self.assertEqual(move6.stock_valuation_layer_ids.unit_cost, 12.0)
        self.assertEqual(move6.stock_valuation_layer_ids.remaining_qty, 0.0)  # already consumed by the next vacuum
        self.assertEqual(move6.stock_valuation_layer_ids.value, 120)

        # vacuum aml, 10@10 should have been 10@12, get rid of 20
        valuation_aml = self._get_stock_valuation_move_lines()
        vacuum_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 8)
        self.assertEqual(vacuum_valuation_aml.balance, -20)
        self.assertEqual(vacuum_valuation_aml.product_id.id, self.product1.id)
        self.assertEqual(vacuum_valuation_aml.quantity, 0)
        self.assertEqual(vacuum_valuation_aml.product_uom_id.id, self.uom_unit.id)

        output_aml = self._get_stock_output_move_lines()
        vacuum_output_aml = output_aml[-1]
        self.assertEqual(len(output_aml), 4)
        self.assertEqual(vacuum_output_aml.balance, 20)

        # ---------------------------------------------------------------------
        # Edit move6, receive less: 2 in negative stock
        # ---------------------------------------------------------------------
        move6.quantity_done = 8

        # stock_account values for move6
        self.assertEqual(move6.stock_valuation_layer_ids.sorted()[-1].remaining_qty, -2)
        self.assertEqual(move6.stock_valuation_layer_ids.sorted()[-1].value, -20)

        # account values for move1
        input_aml = self._get_stock_input_move_lines()
        move6_correction_input_aml = input_aml[-1]
        self.assertEqual(move6_correction_input_aml.debit, 20)
        self.assertEqual(move6_correction_input_aml.credit, 0)

        valuation_aml = self._get_stock_valuation_move_lines()
        move6_correction_valuation_aml = valuation_aml[-1]
        self.assertEqual(move6_correction_valuation_aml.debit, 0)
        self.assertEqual(move6_correction_valuation_aml.credit, 20)
        self.assertEqual(move6_correction_valuation_aml.product_id.id, self.product1.id)
        # FIXME sle
        #self.assertEqual(move6_correction_valuation_aml.quantity, -2)
        self.assertEqual(move6_correction_valuation_aml.product_uom_id.id, self.uom_unit.id)

        # -----------------------------------------------------------
        # receive 4 to counterbalance now
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

        # account values after vacuum
        input_aml = self._get_stock_input_move_lines()
        self.assertEqual(len(input_aml), 7)
        move6_correction2_input_aml = input_aml[-1]
        self.assertEqual(move6_correction2_input_aml.debit, 10)
        self.assertEqual(move6_correction2_input_aml.credit, 0)

        valuation_aml = self._get_stock_valuation_move_lines()
        move6_correction2_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 11)
        self.assertEqual(move6_correction2_valuation_aml.debit, 0)
        self.assertEqual(move6_correction2_valuation_aml.credit, 10)
        self.assertEqual(move6_correction2_valuation_aml.product_id.id, self.product1.id)
        self.assertEqual(move6_correction2_valuation_aml.quantity, 0)
        self.assertEqual(move6_correction_valuation_aml.product_uom_id.id, self.uom_unit.id)

        # ---------------------------------------------------------------------
        # Ending
        # ---------------------------------------------------------------------
        self.assertEqual(self.product1.quantity_svl, 2)
        self.assertEqual(self.product1.value_svl, 30)
        # check on accounting entries
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('debit')), 30)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('credit')), 380)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 380)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 350)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('debit')), 320)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('credit')), 0)

    def test_fifo_perpetual_2(self):
        """ Normal fifo flow (no negative handling) """
        # http://accountingexplained.com/financial/inventories/fifo-method
        self.product1.categ_id.property_cost_method = 'fifo'

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

        self.assertEqual(move1.stock_valuation_layer_ids.value, 1020.0)

        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 68.0)

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

        self.assertEqual(move2.stock_valuation_layer_ids.value, 2170.0)

        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 68.0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 140.0)

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
        self.assertEqual(move3.stock_valuation_layer_ids.value, -1423.0)

        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 114)
        self.assertEqual(move3.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out moves

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

        self.assertEqual(move4.stock_valuation_layer_ids.value, 640.0)

        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 114)
        self.assertEqual(move3.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.stock_valuation_layer_ids.remaining_qty, 40.0)

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

        self.assertEqual(move5.stock_valuation_layer_ids.value, 1287.0)

        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 114)
        self.assertEqual(move3.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.stock_valuation_layer_ids.remaining_qty, 40.0)
        self.assertEqual(move5.stock_valuation_layer_ids.remaining_qty, 78.0)

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
        self.assertEqual(move6.stock_valuation_layer_ids.value, -1799.0)

        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 0)
        self.assertEqual(move3.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.stock_valuation_layer_ids.remaining_qty, 38.0)
        self.assertEqual(move5.stock_valuation_layer_ids.remaining_qty, 78.0)
        self.assertEqual(move6.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out moves

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
        self.assertEqual(move7.stock_valuation_layer_ids.value, -1004.0)

        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 0)
        self.assertEqual(move3.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.stock_valuation_layer_ids.remaining_qty, 0.0)
        self.assertEqual(move5.stock_valuation_layer_ids.remaining_qty, 54.0)
        self.assertEqual(move6.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move7.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out moves

        # send 10 units in our transit location, the valorisation should not be impacted
        transit_location = self.env['stock.location'].search([
            ('company_id', '=', self.env.company.id),
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

        self.assertEqual(move8.stock_valuation_layer_ids.value, 0.0)

        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 0)
        self.assertEqual(move3.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.stock_valuation_layer_ids.remaining_qty, 0.0)
        self.assertEqual(move5.stock_valuation_layer_ids.remaining_qty, 54.0)
        self.assertEqual(move6.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move7.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move8.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in internal moves

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
        self.assertEqual(move9.stock_valuation_layer_ids.value, -165.0)

        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 0)
        self.assertEqual(move3.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.stock_valuation_layer_ids.remaining_qty, 0.0)
        self.assertEqual(move5.stock_valuation_layer_ids.remaining_qty, 44.0)
        self.assertEqual(move6.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move7.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move8.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in internal moves
        self.assertEqual(move9.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out moves

    def test_fifo_perpetual_3(self):
        """ Normal fifo flow (no negative handling) """
        self.product1.categ_id.property_cost_method = 'fifo'

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

        self.assertEqual(move1.stock_valuation_layer_ids.value, 1000.0)

        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 10.0)

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

        self.assertEqual(move2.stock_valuation_layer_ids.value, 800.0)

        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 10.0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 10.0)

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
        self.assertEqual(move3.stock_valuation_layer_ids.value, -1400.0)

        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 5)
        self.assertEqual(move3.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out moves

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

        self.assertEqual(move4.stock_valuation_layer_ids.value, 300.0)

        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 5)
        self.assertEqual(move3.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.stock_valuation_layer_ids.remaining_qty, 5.0)

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
        self.assertEqual(move5.stock_valuation_layer_ids.value, -520.0)

        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 0)
        self.assertEqual(move3.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.stock_valuation_layer_ids.remaining_qty, 3.0)
        self.assertEqual(move5.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out moves

    def test_fifo_perpetual_4(self):
        """ Fifo and return handling. """
        self.product1.categ_id.property_cost_method = 'fifo'

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

        self.assertEqual(move1.stock_valuation_layer_ids.value, 80.0)
        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 8.0)

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


        self.assertEqual(move2.stock_valuation_layer_ids.value, 64)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 4.0)

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
        self.assertEqual(move3.stock_valuation_layer_ids.value, -112.0)

        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 2)
        self.assertEqual(move3.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out moves

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

        self.assertEqual(move4.stock_valuation_layer_ids.value, 12.0)

        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 2)
        self.assertEqual(move3.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.stock_valuation_layer_ids.remaining_qty, 2.0)

        self.assertEqual(self.product1.standard_price, 16)

        # return
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=out_pick.ids, active_id=out_pick.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0 # Return only 2
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.move_lines[0].move_line_ids[0].qty_done = 1.0
        return_pick.action_done()

        self.assertEqual(self.product1.standard_price, 16)

        self.assertEqual(return_pick.move_lines.stock_valuation_layer_ids.unit_cost, 16)

    def test_fifo_negative_1(self):
        """ Send products that you do not have. Value the first outgoing move to the standard
        price, receive in multiple times the delivered quantity and run _fifo_vacuum to compensate.
        """
        self.product1.categ_id.property_cost_method = 'fifo'

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
        self.assertEqual(move1.stock_valuation_layer_ids.value, -400.0)
        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, -50.0)  # normally unused in out moves, but as it moved negative stock we mark it
        self.assertEqual(move1.stock_valuation_layer_ids.unit_cost, 8)

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
        self.assertEqual(move2.stock_valuation_layer_ids.value, 600.0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 0)
        self.assertEqual(move2.stock_valuation_layer_ids.unit_cost, 15.0)

        # ---------------------------------------------------------------------
        # The vacuum ran
        # ---------------------------------------------------------------------
        # account values after vacuum
        valuation_aml = self._get_stock_valuation_move_lines()
        vacuum1_valuation_aml = valuation_aml[-1]
        self.assertEqual(vacuum1_valuation_aml.debit, 0)
        # 280 was credited more in valuation (we compensated 40 items here, so initially 40 were
        # valued at 8 -> 320 in credit but now we actually sent 40@15 = 600, so the difference is
        # 280 more credited)
        self.assertEqual(vacuum1_valuation_aml.credit, 280)
        output_aml = self._get_stock_output_move_lines()
        vacuum1_output_aml = output_aml[-1]
        self.assertEqual(vacuum1_output_aml.debit, 280)
        self.assertEqual(vacuum1_output_aml.credit, 0)

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

        # ---------------------------------------------------------------------
        # The vacuum ran
        # ---------------------------------------------------------------------

        # stock values for move1-3
        self.assertEqual(sum(move1.stock_valuation_layer_ids.mapped('value')), -850.0)  # 40@15 + 10@25
        self.assertEqual(sum(move1.stock_valuation_layer_ids.mapped('remaining_qty')), 0.0)
        self.assertEqual(sum(move2.stock_valuation_layer_ids.mapped('value')), 600.0)
        self.assertEqual(sum(move2.stock_valuation_layer_ids.mapped('remaining_qty')), 0.0)
        self.assertEqual(sum(move3.stock_valuation_layer_ids.mapped('value')), 500.0)
        self.assertEqual(sum(move3.stock_valuation_layer_ids.mapped('remaining_qty')), 10.0)

        # account values after vacuum
        valuation_aml = self._get_stock_valuation_move_lines()
        vacuum2_valuation_aml = valuation_aml[-1]
        self.assertEqual(vacuum2_valuation_aml.debit, 0)
        # there is still 10@8 to compensate with 10@25 -> 170 to credit more in the valuation account
        self.assertEqual(vacuum2_valuation_aml.credit, 170)
        output_aml = self._get_stock_output_move_lines()
        vacuum2_output_aml = output_aml[-1]
        self.assertEqual(vacuum2_output_aml.debit, 170)
        self.assertEqual(vacuum2_output_aml.credit, 0)

        # ---------------------------------------------------------------------
        # Ending
        # ---------------------------------------------------------------------
        self.assertEqual(self.product1.quantity_svl, 10)
        self.assertEqual(self.product1.value_svl, 250)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('debit')), 0)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('credit')), 1100)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 1100)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 850)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('debit')), 850)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('credit')), 0)

    def test_fifo_negative_2(self):
        """ Receives 10 units, send more, the extra quantity should be valued at the last fifo
        price, running the vacuum should not do anything. Receive 2 units at the price the two
        extra units were sent, check that no accounting entries are created.
        """
        self.product1.categ_id.property_cost_method = 'fifo'

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
        self.assertEqual(move1.stock_valuation_layer_ids.value, 100.0)
        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 10.0)
        self.assertEqual(move1.stock_valuation_layer_ids.unit_cost, 10.0)

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
        self.assertEqual(move2.stock_valuation_layer_ids.value, -120.0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, -2.0)

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
        self.product1._run_fifo_vacuum()

        self.assertEqual(move1.stock_valuation_layer_ids.value, 100.0)
        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 0.0)
        self.assertEqual(move1.stock_valuation_layer_ids.unit_cost, 10.0)
        self.assertEqual(move2.stock_valuation_layer_ids.value, -120.0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, -2.0)

        self.assertEqual(len(move1.account_move_ids), 1)
        self.assertEqual(len(move2.account_move_ids), 1)

        self.assertEqual(self.product1.quantity_svl, -2)
        self.assertEqual(self.product1.value_svl, -20)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('debit')), 0)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('credit')), 100)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 100)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 120)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('debit')), 120)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('credit')), 0)

        # Now receive exactly the extra units at exactly the price sent, no
        # accounting entries should be created after the vacuum.
        # ---------------------------------------------------------------------
        # Receive 2@10
        # ---------------------------------------------------------------------
        move3 = self.env['stock.move'].create({
            'name': '10 in',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
            'price_unit': 10,
            'move_line_ids': [(0, 0, {
                'product_id': self.product1.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 2.0,
            })]
        })
        move3._action_confirm()
        move3._action_done()

        # ---------------------------------------------------------------------
        # Ending
        # ---------------------------------------------------------------------
        self.assertEqual(move1.stock_valuation_layer_ids.value, 100.0)
        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 0.0)
        self.assertEqual(move1.stock_valuation_layer_ids.unit_cost, 10.0)
        self.assertEqual(sum(move2.stock_valuation_layer_ids.mapped('value')), -120.0)
        self.assertEqual(sum(move2.stock_valuation_layer_ids.mapped('remaining_qty')), 0)
        self.assertEqual(move3.stock_valuation_layer_ids.value, 20)
        self.assertEqual(move3.stock_valuation_layer_ids.remaining_qty, 0.0)
        self.assertEqual(move3.stock_valuation_layer_ids.unit_cost, 10.0)

        self.assertEqual(len(move1.account_move_ids), 1)
        self.assertEqual(len(move2.account_move_ids), 1)
        self.assertEqual(len(move3.account_move_ids), 1)  # the created account move is due to the receipt

        # nothing should have changed in the accounting regarding the output
        self.assertEqual(self.product1.quantity_svl, 0)
        self.assertEqual(self.product1.value_svl, 0)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('debit')), 0)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('credit')), 120)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 120)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 120)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('debit')), 120)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('credit')), 0)

    def test_fifo_negative_3(self):
        """ Receives 10 units, send 10 units, then send more: the extra quantity should be valued
        at the last fifo price, running the vacuum should not do anything.
        """
        self.product1.categ_id.property_cost_method = 'fifo'

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
        self.assertEqual(move1.stock_valuation_layer_ids.value, 100.0)
        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 10.0)
        self.assertEqual(move1.stock_valuation_layer_ids.unit_cost, 10.0)

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
        self.assertEqual(move2.stock_valuation_layer_ids.value, -100.0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 0.0)

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
        # FIXME sle last fifo price not updated on the product?
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
        self.assertEqual(move3.stock_valuation_layer_ids.value, -210.0)
        self.assertEqual(move3.stock_valuation_layer_ids.remaining_qty, -21.0)

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
        self.product1._run_fifo_vacuum()
        self.assertEqual(len(move3.account_move_ids), 1)

        # the vacuum shouldn't do anything in this case
        self.assertEqual(move1.stock_valuation_layer_ids.value, 100.0)
        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 0.0)
        self.assertEqual(move1.stock_valuation_layer_ids.unit_cost, 10.0)
        self.assertEqual(move2.stock_valuation_layer_ids.value, -100.0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 0.0)
        self.assertEqual(move3.stock_valuation_layer_ids.value, -210.0)
        self.assertEqual(move3.stock_valuation_layer_ids.remaining_qty, -21.0)

        self.assertEqual(len(move1.account_move_ids), 1)
        self.assertEqual(len(move2.account_move_ids), 1)
        self.assertEqual(len(move3.account_move_ids), 1)

        # ---------------------------------------------------------------------
        # Ending
        # ---------------------------------------------------------------------
        self.assertEqual(self.product1.quantity_svl, -21)
        self.assertEqual(self.product1.value_svl, -210)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('debit')), 0)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('credit')), 100)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 100)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 310)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('debit')), 310)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('credit')), 0)

    def test_fifo_add_move_in_done_picking_1(self):
        """ The flow is:

        product2 std price = 20
        IN01 10@10 product1
        IN01 10@20 product2
        IN01 correction 10@20 -> 11@20 (product2)
        DO01 11 product2
        DO02 1 product2
        DO02 correction 1 -> 2 (negative stock)
        IN03 2@30 product2
        vacuum
        """
        self.product1.categ_id.property_cost_method = 'fifo'

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
        self.assertEqual(move1.stock_valuation_layer_ids.value, 100.0)
        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 10.0)
        self.assertEqual(move1.stock_valuation_layer_ids.unit_cost, 10.0)

        # ---------------------------------------------------------------------
        # Add a stock move, receive 10@20 of another product
        # ---------------------------------------------------------------------
        self.product2.categ_id.property_cost_method = 'fifo'
        self.product2.standard_price = 20
        move2 = self.env['stock.move'].create({
            'picking_id': receipt.id,
            'name': '10 in',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'move_line_ids': [(0, 0, {
                'product_id': self.product2.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_id': self.uom_unit.id,
                'qty_done': 10.0,
            })]
        })
        move2._action_done()

        self.assertEqual(move2.stock_valuation_layer_ids.value, 200.0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 10.0)
        self.assertEqual(move2.stock_valuation_layer_ids.unit_cost, 20.0)

        self.assertEqual(self.product1.quantity_svl, 10)
        self.assertEqual(self.product1.value_svl, 100)
        self.assertEqual(self.product2.quantity_svl, 10)
        self.assertEqual(self.product2.value_svl, 200)

        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 300)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 0)

        # ---------------------------------------------------------------------
        # Edit the previous stock move, receive 11
        # ---------------------------------------------------------------------
        move2.quantity_done = 11

        self.assertEqual(sum(move2.stock_valuation_layer_ids.mapped('value')), 220.0)  # after correction, the move should be valued at 11@20
        self.assertEqual(sum(move2.stock_valuation_layer_ids.mapped('remaining_qty')), 11.0)
        self.assertEqual(move2.stock_valuation_layer_ids.sorted()[-1].unit_cost, 20.0)

        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 320)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 0)

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

        self.assertEqual(move3.stock_valuation_layer_ids.value, -220.0)
        self.assertEqual(move3.stock_valuation_layer_ids.remaining_qty, 0.0)
        self.assertEqual(move3.stock_valuation_layer_ids.unit_cost, 20.0)
        self.assertEqual(self.product2.qty_available, 0)
        self.assertEqual(self.product2.quantity_svl, 0)

        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 320)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 220)

        # ---------------------------------------------------------------------
        # Add one move of product 2, this'll make some negative stock.
        # ---------------------------------------------------------------------

        # FIXME: uncomment when negative stock is handled
        #move4 = self.env['stock.move'].create({
        #    'picking_id': delivery.id,
        #    'name': '1 out',
        #    'location_id': self.stock_location.id,
        #    'location_dest_id': self.customer_location.id,
        #    'product_id': self.product2.id,
        #    'product_uom': self.uom_unit.id,
        #    'product_uom_qty': 1.0,
        #    'state': 'done',  # simulate default_get override
        #    'move_line_ids': [(0, 0, {
        #        'product_id': self.product2.id,
        #        'location_id': self.stock_location.id,
        #        'location_dest_id': self.customer_location.id,
        #        'product_uom_id': self.uom_unit.id,
        #        'qty_done': 1.0,
        #    })]
        #})
        #self.assertEqual(move4.value, -20.0)
        #self.assertEqual(move4.remaining_qty, -1.0)
        #self.assertEqual(move4.price_unit, -20.0)

        #self.assertEqual(self.product2.qty_available, -1)

        #self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 320)
        #self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 240)

        ## ---------------------------------------------------------------------
        ## edit the created move, add 1
        ## ---------------------------------------------------------------------
        #move4.quantity_done = 2

        #self.assertEqual(self.product2.qty_available, -2)
        #self.assertEqual(move4.value, -40.0)
        #self.assertEqual(move4.remaining_qty, -2.0)
        #self.assertEqual(move4.price_unit, -20.0)

        #self.assertEqual(sum(self._get_stock_input_move_lines().mapped('debit')), 0)
        #self.assertEqual(sum(self._get_stock_input_move_lines().mapped('credit')), 320) # 10*10 + 11*20
        #self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 320)
        #self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 260)
        #self.assertEqual(sum(self._get_stock_output_move_lines().mapped('debit')), 260)
        #self.assertEqual(sum(self._get_stock_output_move_lines().mapped('credit')), 0)

        #self.env['stock.move']._run_fifo_vacuum()

        #self.assertEqual(sum(self._get_stock_input_move_lines().mapped('debit')), 0)
        #self.assertEqual(sum(self._get_stock_input_move_lines().mapped('credit')), 320) # 10*10 + 11*20
        #self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 320)
        #self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 260)
        #self.assertEqual(sum(self._get_stock_output_move_lines().mapped('debit')), 260)
        #self.assertEqual(sum(self._get_stock_output_move_lines().mapped('credit')), 0)

        ## ---------------------------------------------------------------------
        ## receive 2 products 2 @ 30
        ## ---------------------------------------------------------------------
        #move5 = self.env['stock.move'].create({
        #    'picking_id': receipt.id,
        #    'name': '10 in',
        #    'location_id': self.supplier_location.id,
        #    'location_dest_id': self.stock_location.id,
        #    'product_id': self.product2.id,
        #    'product_uom': self.uom_unit.id,
        #    'product_uom_qty': 2.0,
        #    'price_unit': 30,
        #    'move_line_ids': [(0, 0, {
        #        'product_id': self.product2.id,
        #        'location_id': self.supplier_location.id,
        #        'location_dest_id': self.stock_location.id,
        #        'product_uom_id': self.uom_unit.id,
        #        'qty_done': 2.0,
        #    })]
        #})
        #move5._action_confirm()
        #move5._action_done()

        #self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 380)
        #self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 260)

        ## ---------------------------------------------------------------------
        ## run vacuum
        ## ---------------------------------------------------------------------
        #self.env['stock.move']._run_fifo_vacuum()

        #self.assertEqual(sum(self._get_stock_input_move_lines().mapped('debit')), 0)
        #self.assertEqual(sum(self._get_stock_input_move_lines().mapped('credit')), 380) # 10*10 + 11*20
        #self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 380)
        #self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 280) # 260/
        #self.assertEqual(sum(self._get_stock_output_move_lines().mapped('debit')), 280)
        #self.assertEqual(sum(self._get_stock_output_move_lines().mapped('credit')), 0)

        #self.assertEqual(self.product2.qty_available, 0)
        #self.assertEqual(self.product2.stock_value, 0)
        #self.assertEqual(move4.remaining_value, 0)
        #self.assertEqual(move4.value, -60)  # after correction, the move is valued -(2*30)

    def test_fifo_add_moveline_in_done_move_1(self):
        self.product1.categ_id.property_cost_method = 'fifo'

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
        self.assertEqual(move1.stock_valuation_layer_ids.value, 100.0)
        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 10.0)
        self.assertEqual(move1.stock_valuation_layer_ids.unit_cost, 10.0)

        self.assertEqual(len(move1.account_move_ids), 1)

        # ---------------------------------------------------------------------
        # Add a new move line to receive 10 more
        # ---------------------------------------------------------------------
        self.assertEqual(len(move1.move_line_ids), 1)
        self.env['stock.move.line'].create({
            'move_id': move1.id,
            'product_id': move1.product_id.id,
            'qty_done': 10,
            'product_uom_id': move1.product_uom.id,
            'location_id': move1.location_id.id,
            'location_dest_id': move1.location_dest_id.id,
        })
        self.assertEqual(sum(move1.stock_valuation_layer_ids.mapped('value')), 200.0)
        self.assertEqual(sum(move1.stock_valuation_layer_ids.mapped('remaining_qty')), 20.0)
        self.assertEqual(move1.stock_valuation_layer_ids.sorted()[-1].unit_cost, 10.0)

        self.assertEqual(len(move1.account_move_ids), 2)

        self.assertEqual(self.product1.quantity_svl, 20)
        self.assertEqual(self.product1.value_svl, 200)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('debit')), 0)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('credit')), 200)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 200)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 0)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('debit')), 0)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('credit')), 0)

    def test_fifo_edit_done_move1(self):
        """ Increase OUT done move while quantities are available.
        """
        self.product1.categ_id.property_cost_method = 'fifo'

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
        self.assertEqual(move1.stock_valuation_layer_ids.value, 100.0)
        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 10.0)
        self.assertEqual(move1.stock_valuation_layer_ids.unit_cost, 10.0)

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

        self.assertAlmostEqual(self.product1.quantity_svl, 10.0)
        self.assertEqual(self.product1.value_svl, 100)

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
        self.assertEqual(move2.stock_valuation_layer_ids.value, 120.0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 10.0)
        self.assertEqual(move2.stock_valuation_layer_ids.unit_cost, 12.0)

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

        self.assertAlmostEqual(self.product1.qty_available, 20.0)
        self.assertAlmostEqual(self.product1.quantity_svl, 20.0)
        self.assertEqual(self.product1.value_svl, 220)

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
        self.assertEqual(move3.stock_valuation_layer_ids.value, -80.0)
        self.assertEqual(move3.stock_valuation_layer_ids.remaining_qty, 0.0)

        # account values for move3
        valuation_aml = self._get_stock_valuation_move_lines()
        move3_valuation_aml = valuation_aml[-1]
        self.assertEqual(move3_valuation_aml.debit, 0)  # FIXME sle shiiiiiiieeeeet with_context out move doesn't work?
        output_aml = self._get_stock_output_move_lines()
        move3_output_aml = output_aml[-1]
        self.assertEqual(move3_output_aml.debit, 80)
        self.assertEqual(move3_output_aml.credit, 0)

        self.assertEqual(len(move3.account_move_ids), 1)

        self.assertAlmostEqual(self.product1.qty_available, 12.0)
        self.assertAlmostEqual(self.product1.quantity_svl, 12.0)
        self.assertEqual(self.product1.value_svl, 140)

        # ---------------------------------------------------------------------
        # Edit last move, send 14 instead
        # it should send 2@10 and 4@12
        # ---------------------------------------------------------------------
        move3.quantity_done = 14
        self.assertEqual(move3.product_qty, 14)
        # old value: -80 -(8@10)
        # new value: -148 => -(10@10 + 4@12)
        self.assertEqual(sum(move3.stock_valuation_layer_ids.mapped('value')), -148)

        # account values for move3
        valuation_aml = self._get_stock_valuation_move_lines()
        move3_valuation_aml = valuation_aml[-1]
        self.assertEqual(move3_valuation_aml.debit, 0)
        output_aml = self._get_stock_output_move_lines()
        move3_output_aml = output_aml[-1]
        self.assertEqual(move3_output_aml.debit, 68)
        self.assertEqual(move3_output_aml.credit, 0)

        self.assertEqual(len(move3.account_move_ids), 2)

        self.assertEqual(self.product1.value_svl, 72)

        # ---------------------------------------------------------------------
        # Ending
        # ---------------------------------------------------------------------
        self.assertEqual(self.product1.qty_available, 6)
        self.assertAlmostEqual(self.product1.quantity_svl, 6.0)
        self.assertEqual(self.product1.value_svl, 72)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('debit')), 0)
        self.assertEqual(sum(self._get_stock_input_move_lines().mapped('credit')), 220)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('debit')), 220)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('credit')), 148)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('debit')), 148)
        self.assertEqual(sum(self._get_stock_output_move_lines().mapped('credit')), 0)

    def test_fifo_edit_done_move2(self):
        """ Decrease, then increase OUT done move while quantities are available.
        """
        self.product1.categ_id.property_cost_method = 'fifo'

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
        self.assertEqual(move1.stock_valuation_layer_ids.value, 100.0)
        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 10.0)
        self.assertEqual(move1.stock_valuation_layer_ids.unit_cost, 10.0)

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
        self.assertEqual(move2.stock_valuation_layer_ids.value, -100.0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 0.0)

        # ---------------------------------------------------------------------
        # Actually, send 8 in the last move
        # ---------------------------------------------------------------------
        move2.quantity_done = 8

        self.assertEqual(sum(move2.stock_valuation_layer_ids.mapped('value')), -80.0)  # the move actually sent 8@10

        self.assertEqual(sum(self.product1.stock_valuation_layer_ids.mapped('remaining_qty')), 2)

        self.product1.qty_available = 2
        self.product1.value_svl = 20
        self.product1.quantity_svl = 2

        # ---------------------------------------------------------------------
        # Actually, send 10 in the last move
        # ---------------------------------------------------------------------
        move2.quantity_done = 10

        self.assertEqual(sum(move2.stock_valuation_layer_ids.mapped('value')), -100.0)  # the move actually sent 10@10
        self.assertEqual(sum(self.product1.stock_valuation_layer_ids.mapped('remaining_qty')), 0)

        self.assertEqual(self.product1.quantity_svl, 0)
        self.assertEqual(self.product1.value_svl, 0)

    def test_average_perpetual_1(self):
        # http://accountingexplained.com/financial/inventories/avco-method
        self.product1.categ_id.property_cost_method = 'average'

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

        self.assertEqual(move1.stock_valuation_layer_ids.value, 900.0)

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

        self.assertEqual(move2.stock_valuation_layer_ids.value, 2170.0)

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

        self.assertEqual(move3.stock_valuation_layer_ids.value, -2916.5)

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

        self.assertEqual(move4.stock_valuation_layer_ids.value, 1120.0)

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

        self.assertEqual(move5.stock_valuation_layer_ids.value, -477.6)

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

        self.assertEqual(move6.stock_valuation_layer_ids.value, 0)

    def test_average_perpetual_2(self):
        self.product1.categ_id.property_cost_method = 'average'

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
        self.assertEqual(self.product1.standard_price, 10)

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
        self.assertEqual(self.product1.standard_price, 12.5)

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
        self.assertEqual(self.product1.standard_price, 12.5)

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
        self.assertEqual(self.product1.standard_price, 12.5)
        self.assertEqual(self.product1.quantity_svl, -5)
        self.assertEqual(self.product1.value_svl, -62.5)

        move2.move_line_ids.qty_done = 20

        self.assertEqual(self.product1.quantity_svl, 5)
        self.assertEqual(self.product1.value_svl, 87.5)

    def test_average_perpetual_3(self):
        self.product1.categ_id.property_cost_method = 'average'

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
        self.assertEqual(self.product1.value_svl, -187.5)

    def test_average_perpetual_4(self):
        """receive 1@10, receive 1@5 insteadof 3@5"""
        self.product1.categ_id.property_cost_method = 'average'

        move1 = self.env['stock.move'].create({
            'name': 'Receive 1 unit at 10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1.0
        move1._action_done()

        move2 = self.env['stock.move'].create({
            'name': 'Receive 3 units at 5',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 3.0,
            'price_unit': 5,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 1.0
        move2._action_done()

        self.assertAlmostEqual(self.product1.quantity_svl, 2.0)
        self.assertAlmostEqual(self.product1.standard_price, 7.5)

    def test_average_perpetual_5(self):
        ''' Set owner on incoming move => no valuation '''
        self.product1.categ_id.property_cost_method = 'average'

        move1 = self.env['stock.move'].create({
            'name': 'Receive 1 unit at 10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1.0
        move1.move_line_ids.owner_id = self.owner1.id
        move1._action_done()

        self.assertAlmostEqual(self.product1.quantity_svl, 0.0)
        self.assertAlmostEqual(self.product1.value_svl, 0.0)

    def test_average_perpetual_6(self):
        """ Batch validation of moves """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'

        move1 = self.env['stock.move'].create({
            'name': 'Receive 1 unit at 10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1.0

        move2 = self.env['stock.move'].create({
            'name': 'Receive 1 units at 5',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'price_unit': 5,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 1.0

        # Receive both at the same time
        (move1 | move2)._action_done()

        self.assertAlmostEqual(self.product1.standard_price, 7.5)
        self.assertEqual(self.product1.quantity_svl, 2)
        self.assertEqual(self.product1.value_svl, 15)

    def test_average_perpetual_7(self):
        """ Test edit in the past. Receive 5@10, receive 10@20, edit the first move to receive
        15 instead.
        """
        self.product1.categ_id.property_cost_method = 'average'

        move1 = self.env['stock.move'].create({
            'name': 'IN 5@10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1.quantity_done = 5
        move1._action_done()

        self.assertAlmostEqual(self.product1.standard_price, 10)
        self.assertAlmostEqual(move1.stock_valuation_layer_ids.value, 50)
        self.assertAlmostEqual(self.product1.quantity_svl, 5)
        self.assertAlmostEqual(self.product1.value_svl, 50)

        move2 = self.env['stock.move'].create({
            'name': 'IN 10@20',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10,
            'price_unit': 20,
        })
        move2._action_confirm()
        move2.quantity_done = 10
        move2._action_done()

        self.assertAlmostEqual(self.product1.standard_price, 16.67)
        self.assertAlmostEqual(move2.stock_valuation_layer_ids.value, 200)
        self.assertAlmostEqual(self.product1.quantity_svl, 15)
        self.assertAlmostEqual(self.product1.value_svl, 250)

        move1.move_line_ids.qty_done = 15

        self.assertAlmostEqual(self.product1.standard_price, 14.0)
        self.assertAlmostEqual(len(move1.stock_valuation_layer_ids), 2)
        self.assertAlmostEqual(move1.stock_valuation_layer_ids.sorted()[-1].value, 100)
        self.assertAlmostEqual(self.product1.quantity_svl, 25)
        self.assertAlmostEqual(self.product1.value_svl, 350)

    def test_average_perpetual_8(self):
        """ Receive 1@10, then dropship 1@20, finally return the dropship. Dropship should not
            impact the price.
        """
        self.product1.categ_id.property_cost_method = 'average'

        move1 = self.env['stock.move'].create({
            'name': 'IN 1@10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1.quantity_done = 1
        move1._action_done()

        self.assertAlmostEqual(self.product1.standard_price, 10)

        move2 = self.env['stock.move'].create({
            'name': 'IN 1@20',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'price_unit': 20,
        })
        move2._action_confirm()
        move2.quantity_done = 1
        move2._action_done()

        self.assertAlmostEqual(self.product1.standard_price, 10.0)

        move3 = self.env['stock.move'].create({
            'name': 'IN 1@20',
            'location_id': self.customer_location.id,
            'location_dest_id': self.supplier_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'price_unit': 20,
        })
        move3._action_confirm()
        move3.quantity_done = 1
        move3._action_done()

        self.assertAlmostEqual(self.product1.standard_price, 10.0)

    def test_average_perpetual_8(self):
        """ When a product has an available quantity of -5, edit an incoming shipment and increase
        the received quantity by 5 units.
        """
        self.product1.categ_id.property_cost_method = 'average'
        # receive 10
        move1 = self.env['stock.move'].create({
            'name': 'IN 5@10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1.quantity_done = 10
        move1._action_done()

        # deliver 15
        move2 = self.env['stock.move'].create({
            'name': 'Deliver 10 units',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 15.0,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 15.0
        move2._action_done()

        # increase the receipt to 15
        move1.move_line_ids.qty_done = 15

    def test_average_negative_1(self):
        """ Test edit in the past. Receive 10, send 20, edit the second move to only send 10.
        """
        self.product1.categ_id.property_cost_method = 'average'

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
        self.product1.categ_id.property_cost_method = 'average'

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
        move1.quantity_done = 10.0
        move1._action_done()
        self.assertEqual(move1.stock_valuation_layer_ids.value, -990.0)  # as no move out were done for this product, fallback on the standard price

    def test_average_negative_3(self):
        """ Send goods that you don't have in stock but received and send some units before.
        """
        self.product1.categ_id.property_cost_method= 'average'

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

        self.assertEqual(move1.stock_valuation_layer_ids.value, 100.0)

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

        self.assertEqual(move2.stock_valuation_layer_ids.value, -100.0)
        self.assertEqual(move2.stock_valuation_layer_ids.remaining_qty, 0.0)  # unused in average move

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
        move3.quantity_done = 10.0
        move3._action_done()

        self.assertEqual(move3.stock_valuation_layer_ids.value, -100.0)  # as no move out were done for this product, fallback on latest cost

    def test_average_negative_4(self):
        self.product1.categ_id.property_cost_method = 'average'

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

        self.assertEqual(move1.stock_valuation_layer_ids.value, 100.0)

    def test_average_negative_5(self):
        self.product1.categ_id.property_cost_method = 'average'

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

        self.assertEqual(move1.stock_valuation_layer_ids.value, 100.0)
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

        self.assertEqual(move2.stock_valuation_layer_ids.value, 200.0)
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
        move3.quantity_done = 5.0
        move3._action_done()

        self.assertEqual(move3.stock_valuation_layer_ids.value, -75.0)
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
        move4.quantity_done = 30.0
        move4._action_done()

        self.assertEqual(move4.stock_valuation_layer_ids.value, -450.0)
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

        self.assertEqual(move5.stock_valuation_layer_ids.value, 400.0)
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
        move6.quantity_done = 5.0
        move6._action_done()

        self.assertEqual(move6.stock_valuation_layer_ids.value, -175.0)
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

        self.assertEqual(move7.stock_valuation_layer_ids.value, 100.0)
        self.assertEqual(self.product1.standard_price, 10)

    def test_average_manual_1(self):
        ''' Set owner on incoming move => no valuation '''
        self.product1.categ_id.property_cost_method = 'average'
        self.product1.categ_id.property_valuation = 'manual_periodic'

        move1 = self.env['stock.move'].create({
            'name': 'Receive 1 unit at 10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1.0
        move1.move_line_ids.owner_id = self.owner1.id
        move1._action_done()

        self.assertAlmostEqual(self.product1.quantity_svl, 0.0)
        self.assertAlmostEqual(self.product1.value_svl, 0.0)

    def test_standard_perpetual_1(self):
        ''' Set owner on incoming move => no valuation '''
        self.product1.categ_id.property_cost_method = 'standard'

        move1 = self.env['stock.move'].create({
            'name': 'Receive 1 unit at 10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1.0
        move1.move_line_ids.owner_id = self.owner1.id
        move1._action_done()

        self.assertAlmostEqual(self.product1.qty_available, 1.0)
        self.assertAlmostEqual(self.product1.quantity_svl, 0.0)
        self.assertAlmostEqual(self.product1.value_svl, 0.0)

    def test_standard_manual_1(self):
        ''' Set owner on incoming move => no valuation '''
        self.product1.categ_id.property_cost_method = 'standard'
        self.product1.categ_id.property_valuation = 'manual_periodic'

        move1 = self.env['stock.move'].create({
            'name': 'Receive 1 unit at 10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 1.0
        move1.move_line_ids.owner_id = self.owner1.id
        move1._action_done()

        self.assertAlmostEqual(self.product1.qty_available, 1.0)
        self.assertAlmostEqual(self.product1.quantity_svl, 0.0)
        self.assertAlmostEqual(self.product1.value_svl, 0.0)

    def test_standard_manual_2(self):
        """Validate a receipt as a regular stock user."""
        self.product1.categ_id.property_cost_method = 'standard'
        self.product1.categ_id.property_valuation = 'manual_periodic'

        self.product1.with_user(self.inventory_user)._change_standard_price(10)

        move1 = self.env['stock.move'].with_user(self.inventory_user).create({
            'name': 'IN 10 units',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10.0
        move1._action_done()

    def test_standard_perpetual_1(self):
        """Validate a receipt as a regular stock user."""
        self.product1.categ_id.property_cost_method = 'standard'
        self.product1.categ_id.property_valuation = 'real_time'

        self.product1.with_user(self.inventory_user)._change_standard_price(10)

        move1 = self.env['stock.move'].with_user(self.inventory_user).create({
            'name': 'IN 10 units',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10.0
        move1._action_done()

    def test_change_cost_method_1(self):
        """ Change the cost method from FIFO to AVCO.
        """
        # ---------------------------------------------------------------------
        # Use FIFO, make some operations
        # ---------------------------------------------------------------------
        self.product1.categ_id.property_cost_method = 'fifo'

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

        self.assertAlmostEqual(self.product1.quantity_svl, 19)
        self.assertEqual(self.product1.value_svl, 240)

        # ---------------------------------------------------------------------
        # Change the production valuation to AVCO
        # ---------------------------------------------------------------------
        self.product1.categ_id.property_cost_method = 'average'

        # valuation should stay to ~240
        self.assertAlmostEqual(self.product1.quantity_svl, 19)
        self.assertAlmostEqual(self.product1.value_svl, 285, delta=0.03)

        # an accounting entry should be created
        # FIXME sle check it

        self.assertEqual(self.product1.standard_price, 15)

    def test_change_cost_method_2(self):
        """ Change the cost method from FIFO to standard.
        """
        # ---------------------------------------------------------------------
        # Use FIFO, make some operations
        # ---------------------------------------------------------------------
        self.product1.categ_id.property_cost_method = 'fifo'

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

        self.assertAlmostEqual(self.product1.quantity_svl, 19)
        self.assertEqual(self.product1.value_svl, 240)

        # ---------------------------------------------------------------------
        # Change the production valuation to AVCO
        # ---------------------------------------------------------------------
        self.product1.categ_id.property_cost_method = 'standard'

        # valuation should stay to ~240
        self.assertAlmostEqual(self.product1.value_svl, 285, delta=0.03)
        self.assertAlmostEqual(self.product1.quantity_svl, 19)

        # no accounting entry should be created
        # FIXME sle check it

        self.assertEqual(self.product1.standard_price, 15)

    def test_fifo_sublocation_valuation_1(self):
        """ Set the main stock as a view location. Receive 2 units of a
        product, put 1 unit in an internal sublocation and the second
        one in a scrap sublocation. Only a single unit, the one in the
        internal sublocation, should be valued. Then, send these two
        quants to a customer, only the one in the internal location
        should be valued.
        """
        self.product1.categ_id.property_cost_method = 'fifo'

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
        self.assertEqual(move1.stock_valuation_layer_ids.value, 10)
        self.assertEqual(move1.stock_valuation_layer_ids.remaining_qty, 1)
        self.assertAlmostEqual(self.product1.qty_available, 0.0)
        self.assertAlmostEqual(self.product1.quantity_svl, 1.0)
        self.assertEqual(self.product1.value_svl, 10)
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
        self.assertEqual(move2.stock_valuation_layer_ids.value, -10)

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

    def test_at_date_standard_1(self):
        self.product1.categ_id.property_cost_method = 'standard'

        now = Datetime.now()
        date1 = now - timedelta(days=8)
        date2 = now - timedelta(days=7)
        date3 = now - timedelta(days=6)
        date4 = now - timedelta(days=5)
        date5 = now - timedelta(days=4)
        date6 = now - timedelta(days=3)
        date7 = now - timedelta(days=2)
        date8 = now - timedelta(days=1)

        # set the standard price to 10
        self.product1._change_standard_price(10, self.expense_account.id)

        # receive 10
        move1 = self.env['stock.move'].create({
            'name': 'in 10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10
        move1._action_done()
        move1.date = date2
        move1.stock_valuation_layer_ids._write({'create_date': date2})

        self.assertEqual(self.product1.quantity_svl, 10)
        self.assertEqual(self.product1.value_svl, 100)

        # receive 20
        move2 = self.env['stock.move'].create({
            'name': 'in 10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 20,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 20
        move2._action_done()
        move2.date = date3
        move2.stock_valuation_layer_ids._write({'create_date': date3})

        self.assertEqual(self.product1.quantity_svl, 30)
        self.assertEqual(self.product1.value_svl, 300)

        # send 15
        move3 = self.env['stock.move'].create({
            'name': 'out 10',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 15,
        })
        move3._action_confirm()
        move3._action_assign()
        move3.move_line_ids.qty_done = 15
        move3._action_done()
        move3.date = date4
        move3.stock_valuation_layer_ids._write({'create_date': date4})

        self.assertEqual(self.product1.quantity_svl, 15)
        self.assertEqual(self.product1.value_svl, 150)

        # set the standard price to 5
        self.product1._change_standard_price(5, self.expense_account.id)
        self.product1.stock_valuation_layer_ids.sorted()[-1]._write({'create_date': date5})

        self.assertEqual(self.product1.quantity_svl, 15)
        self.assertEqual(self.product1.value_svl, 75)

        # send 20
        move4 = self.env['stock.move'].create({
            'name': 'out 10',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 20,
        })
        move4._action_confirm()
        move4._action_assign()
        move4.move_line_ids.qty_done = 20
        move4._action_done()
        move4.date = date6
        move4.stock_valuation_layer_ids._write({'create_date': date6})

        self.assertEqual(self.product1.quantity_svl, -5)
        self.assertEqual(self.product1.value_svl, -25)

        # set the standard price to 7.5
        self.product1._change_standard_price(7.5, self.expense_account.id)
        self.product1.stock_valuation_layer_ids.sorted()[-1]._write({'create_date': date7})

        # receive 100
        move5 = self.env['stock.move'].create({
            'name': 'in 10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100,
        })
        move5._action_confirm()
        move5._action_assign()
        move5.move_line_ids.qty_done = 100
        move5._action_done()
        move5.date = date8
        move5.stock_valuation_layer_ids._write({'create_date': date8})

        self.assertEqual(self.product1.quantity_svl, 95)
        self.assertEqual(self.product1.value_svl, 712.5)

        # Quantity available at date
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date1)).quantity_svl, 0)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date2)).quantity_svl, 10)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date3)).quantity_svl, 30)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date4)).quantity_svl, 15)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date5)).quantity_svl, 15)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date6)).quantity_svl, -5)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date7)).quantity_svl, -5)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date8)).quantity_svl, 95)

        # Valuation at date
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date1)).value_svl, 0)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date2)).value_svl, 100)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date3)).value_svl, 300)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date4)).value_svl, 150)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date5)).value_svl, 75)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date6)).value_svl, -25)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date8)).value_svl, 712.5)

        # edit the done quantity of move1, decrease it
        move1.quantity_done = 5

        # the change is only visible right now
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date2)).quantity_svl, 10)
        self.assertEqual(self.product1.quantity_svl, 90)
        # as when we decrease a quantity on a recreipt, we consider it as a out move with the price
        # of today, the value will be decrease of 100 - (5*7.5)
        self.assertEqual(sum(move1.stock_valuation_layer_ids.mapped('value')), 62.5)
        # but the change is still only visible right now
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date2)).value_svl, 100)

        # edit move 4, send 15 instead of 20
        move4.quantity_done = 15
        # -(20*5) + (5*7.5)
        self.assertEqual(sum(move4.stock_valuation_layer_ids.mapped('value')), -62.5)

        # the change is only visible right now
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date6)).value_svl, -25)

        self.assertEqual(self.product1.quantity_svl, 95)
        self.assertEqual(self.product1.value_svl, 712.5)

    def test_at_date_fifo_1(self):
        """ Make some operations at different dates, check that the results of the valuation at
        date wizard are consistent. Afterwards, edit the done quantity of some operations. The
        valuation at date results should take these changes into account.
        """
        self.product1.categ_id.property_cost_method = 'fifo'

        now = Datetime.now()
        date1 = now - timedelta(days=8)
        date2 = now - timedelta(days=7)
        date3 = now - timedelta(days=6)
        date4 = now - timedelta(days=5)
        date5 = now - timedelta(days=4)
        date6 = now - timedelta(days=3)

        # receive 10@10
        move1 = self.env['stock.move'].create({
            'name': 'in 10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10
        move1._action_done()
        move1.date = date1
        move1.stock_valuation_layer_ids._write({'create_date': date1})

        self.assertEqual(self.product1.quantity_svl, 10)
        self.assertEqual(self.product1.value_svl, 100)

        # receive 10@12
        move2 = self.env['stock.move'].create({
            'name': 'in 10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10,
            'price_unit': 12,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 10
        move2._action_done()
        move2.date = date2
        move2.stock_valuation_layer_ids._write({'create_date': date2})

        self.assertAlmostEqual(self.product1.quantity_svl, 20)
        self.assertEqual(self.product1.value_svl, 220)

        # send 15
        move3 = self.env['stock.move'].create({
            'name': 'out 10',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 15,
        })
        move3._action_confirm()
        move3._action_assign()
        move3.move_line_ids.qty_done = 15
        move3._action_done()
        move3.date = date3
        move3.stock_valuation_layer_ids._write({'create_date': date3})

        self.assertAlmostEqual(self.product1.quantity_svl, 5.0)
        self.assertEqual(self.product1.value_svl, 60)

        # send 20
        move4 = self.env['stock.move'].create({
            'name': 'out 10',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 20,
        })
        move4._action_confirm()
        move4._action_assign()
        move4.move_line_ids.qty_done = 20
        move4._action_done()
        move4.date = date4
        move4.stock_valuation_layer_ids._write({'create_date': date4})

        self.assertAlmostEqual(self.product1.quantity_svl, -15.0)
        self.assertEqual(self.product1.value_svl, -180)

        # receive 100@15
        move5 = self.env['stock.move'].create({
            'name': 'in 10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 100,
            'price_unit': 15,
        })
        move5._action_confirm()
        move5._action_assign()
        move5.move_line_ids.qty_done = 100
        move5._action_done()
        move5.date = date5
        move5.stock_valuation_layer_ids._write({'create_date': date5})

        # the vacuum ran
        move4.stock_valuation_layer_ids.sorted()[-1]._write({'create_date': date6})

        self.assertEqual(self.product1.quantity_svl, 85)
        self.assertEqual(self.product1.value_svl, 1275)

        # Edit the quantity done of move1, increase it.
        move1.quantity_done = 20

        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date1)).quantity_svl, 10)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date1)).value_svl, 100)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date2)).quantity_svl, 20)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date2)).value_svl, 220)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date3)).quantity_svl, 5)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date3)).value_svl, 60)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date4)).quantity_svl, -15)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date4)).value_svl, -180)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date5)).quantity_svl, 85)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date5)).value_svl, 1320)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date6)).quantity_svl, 85)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date6)).value_svl, 1275)
        self.assertEqual(self.product1.quantity_svl, 95)
        self.assertEqual(self.product1.value_svl, 1375)

    def test_at_date_fifo_2(self):
        self.product1.categ_id.property_cost_method = 'fifo'

        now = Datetime.now()
        date1 = now - timedelta(days=8)
        date2 = now - timedelta(days=7)
        date3 = now - timedelta(days=6)
        date4 = now - timedelta(days=5)
        date5 = now - timedelta(days=4)

        # receive 10@10
        move1 = self.env['stock.move'].create({
            'name': 'in 10@10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10
        move1._action_done()
        move1.date = date1
        move1.stock_valuation_layer_ids._write({'create_date': date1})

        self.assertAlmostEqual(self.product1.quantity_svl, 10.0)
        self.assertEqual(self.product1.value_svl, 100)

        # receive 10@15
        move2 = self.env['stock.move'].create({
            'name': 'in 10@15',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10,
            'price_unit': 15,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 10
        move2._action_done()
        move2.date = date2
        move2.stock_valuation_layer_ids._write({'create_date': date2})

        self.assertAlmostEqual(self.product1.quantity_svl, 20.0)
        self.assertEqual(self.product1.value_svl, 250)

        # send 30
        move3 = self.env['stock.move'].create({
            'name': 'out 30',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 30,
        })
        move3._action_confirm()
        move3._action_assign()
        move3.move_line_ids.qty_done = 30
        move3._action_done()
        move3.date = date3
        move3.stock_valuation_layer_ids._write({'create_date': date3})

        self.assertAlmostEqual(self.product1.quantity_svl, -10.0)
        self.assertEqual(self.product1.value_svl, -150)

        # receive 10@20
        move4 = self.env['stock.move'].create({
            'name': 'in 10@20',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10,
            'price_unit': 20,
        })
        move4._action_confirm()
        move4._action_assign()
        move4.move_line_ids.qty_done = 10
        move4._action_done()
        move4.date = date4
        move3.stock_valuation_layer_ids.sorted()[-1]._write({'create_date': date4})
        move4.stock_valuation_layer_ids._write({'create_date': date4})

        self.assertAlmostEqual(self.product1.quantity_svl, 0.0)
        self.assertEqual(self.product1.value_svl, 0)

        # receive 10@10
        move5 = self.env['stock.move'].create({
            'name': 'in 10@10',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10,
            'price_unit': 10,
        })
        move5._action_confirm()
        move5._action_assign()
        move5.move_line_ids.qty_done = 10
        move5._action_done()
        move5.date = date5
        move5.stock_valuation_layer_ids._write({'create_date': date5})

        self.assertAlmostEqual(self.product1.quantity_svl, 10.0)
        self.assertEqual(self.product1.value_svl, 100)

        # ---------------------------------------------------------------------
        # ending: perpetual valuation
        # ---------------------------------------------------------------------
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date1)).quantity_svl, 10)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date1)).value_svl, 100)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date2)).quantity_svl, 20)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date2)).value_svl, 250)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date3)).quantity_svl, -10)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date3)).value_svl, -150)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date4)).quantity_svl, 0)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date4)).value_svl, 0)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date5)).quantity_svl, 10)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date5)).value_svl, 100)
        self.assertEqual(self.product1.quantity_svl, 10)
        self.assertEqual(self.product1.value_svl, 100)

    def test_inventory_fifo_1(self):
        """ Make an inventory from a location with a company set, and ensure the product has a stock
        value. When the product is sold, ensure there is no remaining quantity on the original move
        and no stock value.
        """
        self.product1.standard_price = 15
        self.product1.categ_id.property_cost_method = 'fifo'
        inventory_location = self.product1.property_stock_inventory
        inventory_location.company_id = self.env.company.id

        # Start Inventory: 12 units
        move1 = self.env['stock.move'].create({
            'name': 'Adjustment of 12 units',
            'location_id': inventory_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 12.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 12.0
        move1._action_done()

        self.assertAlmostEqual(move1.stock_valuation_layer_ids.value, 180.0)
        self.assertAlmostEqual(move1.stock_valuation_layer_ids.remaining_qty, 12.0)
        self.assertAlmostEqual(self.product1.value_svl, 180.0)

        # Sell the 12 units
        move2 = self.env['stock.move'].create({
            'name': 'Sell 12 units',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 12.0,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 12.0
        move2._action_done()

        self.assertAlmostEqual(move1.stock_valuation_layer_ids.remaining_qty, 0.0)
        self.assertAlmostEqual(self.product1.value_svl, 0.0)

    def test_at_date_average_1(self):
        """ Set a company on the inventory loss, take items from there then put items there, check
        the values and quantities at date.
        """
        now = Datetime.now()
        date1 = now - timedelta(days=8)
        date2 = now - timedelta(days=7)

        self.product1.standard_price = 10
        self.product1.product_tmpl_id.cost_method = 'average'
        inventory_location = self.product1.property_stock_inventory
        inventory_location.company_id = self.env.company.id

        move1 = self.env['stock.move'].create({
            'name': 'Adjustment of 10 units',
            'location_id': inventory_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 10.0
        move1._action_done()
        move1.date = date1
        move1.stock_valuation_layer_ids._write({'create_date': date1})

        move2 = self.env['stock.move'].create({
            'name': 'Sell 5 units',
            'location_id': self.stock_location.id,
            'location_dest_id': inventory_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.qty_done = 5.0
        move2._action_done()
        move2.date = date2
        move2.stock_valuation_layer_ids._write({'create_date': date2})

        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date1)).quantity_svl, 10)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date1)).value_svl, 100)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date2)).quantity_svl, 5)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date2)).value_svl, 50)
