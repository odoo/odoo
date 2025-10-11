# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import UserError
from odoo.fields import Datetime
from odoo.tests import Form

from odoo.addons.stock_account.tests.common import TestStockValuationCommon


def _create_accounting_data(env):
    """Create the accounts and journals used in stock valuation.

    :param env: environment used to create the records
    :return: an input account, an output account, a valuation account, an expense account, a stock journal
    """
    stock_valuation_account = env['account.account'].create({
        'name': 'Stock Valuation',
        'code': 'StockValuation',
        'account_type': 'asset_current',
        'reconcile': True,
    })
    expense_account = env['account.account'].create({
        'name': 'Expense Account',
        'code': 'ExpenseAccount',
        'account_type': 'expense',
        'reconcile': True,
    })
    income_account = env['account.account'].create({
        'name': 'Income Account',
        'code': 'IncomeAccount',
        'account_type': 'income',
        'reconcile': True,
    })
    stock_journal = env['account.journal'].create({
        'name': 'Stock Journal',
        'code': 'STJTEST',
        'type': 'general',
    })
    return stock_valuation_account, expense_account, income_account, stock_journal


class TestStockValuationBase(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.EUR').active = True
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')
        cls.partner = cls.env['res.partner'].create({'name': 'xxx'})
        cls.owner1 = cls.env['res.partner'].create({'name': 'owner1'})
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.product1 = cls.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'default_code': 'prda',
            'categ_id': cls.env.ref('product.product_category_goods').id,
        })
        cls.product2 = cls.env['product.product'].create({
            'name': 'Product B',
            'is_storable': True,
            'categ_id': cls.env.ref('product.product_category_goods').id,
        })
        cls.inventory_user = cls.env['res.users'].create({
            'name': 'Pauline Poivraisselle',
            'login': 'pauline',
            'email': 'p.p@example.com',
            'notification_type': 'inbox',
            'group_ids': [(6, 0, [cls.env.ref('stock.group_stock_user').id])]
        })

        cls.stock_valuation_account, cls.expense_account, cls.income_account, cls.stock_journal = _create_accounting_data(cls.env)
        cls.stock_valuation_account.account_stock_variation_id = cls.expense_account
        cls.env.company.account_stock_journal_id = cls.stock_journal
        cls.product1.property_account_expense_id = cls.expense_account.id
        cls.inventory_loss_location = cls.env['stock.location'].search(
            [('usage', '=', 'inventory'), ('company_id', '=', cls.env.company.id)
        ], limit=1)
        cls.inventory_adjustment_account = cls.env['account.account'].create({
            'name': 'Inventory Adjustment Account',
            'code': 'INVADJ',
            'account_type': 'expense',
            'reconcile': True,
        })
        cls.inventory_loss_location.valuation_account_id = cls.inventory_adjustment_account
        cls.product1.categ_id.write({
            'property_stock_valuation_account_id': cls.stock_valuation_account.id,
            'property_stock_journal': cls.stock_journal.id,
        })
        cls.product1.categ_id.property_valuation = 'real_time'
        cls.product2.categ_id.property_valuation = 'real_time'
        cls.product1.write({
            'property_account_income_id': cls.income_account.id,
            'property_account_expense_id': cls.expense_account.id,
        })

    def _get_stock_valuation_move_lines(self):
        return self.env['account.move.line'].search([
            ('account_id', '=', self.stock_valuation_account.id),
        ], order='date, id')

    def _get_expense_move_lines(self):
        return self.env['account.move.line'].search([
            ('account_id', '=', self.expense_account.id),
        ], order='date, id')


class TestStockValuation(TestStockValuationBase):
    def test_realtime(self):
        """ Stock moves update stock value with product x cost price,
        price change updates the stock value based on current stock level.
        """
        # Enter 10 products while price is 5.0
        self.product1.standard_price = 5.0
        move1 = self._make_in_move(self.product1, 10, 5)

        closing_move = self._close()
        debit_line = closing_move.line_ids.filtered(lambda l: l.debit > 0)
        self.assertEqual(len(debit_line), 1)
        self.assertEqual(debit_line.debit, 50.0)
        self.assertEqual(debit_line.credit, 0)
        self.product1._invalidate_cache()

        # Set price to 6.0
        self.product1.standard_price = 6.0
        closing_move = self._close()
        debit_line = closing_move.line_ids.filtered(lambda l: l.debit > 0)
        self.assertEqual(len(debit_line), 1)
        self.assertEqual(debit_line.debit, 10.0)
        self.assertEqual(debit_line.credit, 0)
        self.assertEqual(move1.product_id, self.product1)

    def test_realtime_consumable(self):
        """ An automatic consumable product should not create any account move entries"""
        # Enter 10 products while price is 5.0
        self.product1.standard_price = 5.0
        self.product1.is_storable = False
        self._make_in_move(self.product1, 10, 5)
        with self.assertRaises(UserError):
            self._close()

    def test_fifo_perpetual_1(self):
        self.product1.categ_id.property_cost_method = 'fifo'

        # ---------------------------------------------------------------------
        # receive 10 units @ 10.00 per unit
        # ---------------------------------------------------------------------
        move1 = self._make_in_move(self.product1, 10, 10)

        # stock_account values for move1
        self.assertEqual(move1._get_price_unit(), 10.0)
        self.assertEqual(move1.remaining_qty, 10.0)
        self.assertEqual(move1.value, 100.0)

        # ---------------------------------------------------------------------
        # receive 10 units @ 8.00 per unit
        # ---------------------------------------------------------------------
        move2 = self._make_in_move(self.product1, 10, 8)

        # stock_account values for move2
        self.assertEqual(move2.remaining_qty, 10.0)
        self.assertEqual(move2.value, 80.0)

        # ---------------------------------------------------------------------
        # sale 3 units
        # ---------------------------------------------------------------------
        move3 = self._make_out_move(self.product1, 3)

        # stock_account values for move3
        self.assertEqual(move3.value, 30.0)  # took 3 items from move 1 @ 10.00 per unit

        # ---------------------------------------------------------------------
        # Increase received quantity of move1 from 10 to 12, it should create
        # a new stock layer at the top of the queue.
        # ---------------------------------------------------------------------
        self._set_quantity(move1, 12)

        # stock_account values for move3
        self.assertEqual(move1._get_price_unit(), 10.0)
        self.assertEqual(move1.remaining_qty, 9.0)
        self.assertEqual(move1.value, 120.0)  # move 1 is now 10@10 + 2@10

        # ---------------------------------------------------------------------
        # Sale 9 units, the units available from the previous increase are not sent
        # immediately as the new layer is at the top of the queue.
        # ---------------------------------------------------------------------
        move4 = self._make_out_move(self.product1, 9)

        # stock_account values for move4
        self.assertEqual(move4.value, 90.0)  # took 9 items from move 1 @ 10.00 per unit

        # ---------------------------------------------------------------------
        # Sale 20 units, we fall in negative stock for 10 units. Theses are
        # valued at the last FIFO cost and the total is negative.
        # ---------------------------------------------------------------------
        move5 = self._make_out_move(self.product1, 20)

        # stock_account values for move5
        self.assertEqual(move5.value, 160.0)
        closing_move = self._close()
        valuation_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.stock_valuation_account)
        expense_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.expense_account)
        self.assertRecordValues(
            valuation_aml + expense_aml,
            [
                {'account_id': self.stock_valuation_account.id, 'debit': 0, 'credit': 80},
                {'account_id': self.expense_account.id, 'debit': 80, 'credit': 0},
            ]
        )

        # ---------------------------------------------------------------------
        # Receive 10 units @ 12.00 to counterbalance the negative, the vacuum
        # will be called directly: 10@10 should be revalued 10@12
        # ---------------------------------------------------------------------
        move6 = self._make_in_move(self.product1, 10, 12)

        self.assertEqual(move6.value, 120.0)
        closing_move = self._close()
        valuation_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.stock_valuation_account)
        expense_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.expense_account)
        self.assertRecordValues(
            valuation_aml + expense_aml,
            [
                {'account_id': self.stock_valuation_account.id, 'debit': 80, 'credit': 0},
                {'account_id': self.expense_account.id, 'debit': 0, 'credit': 80},
            ]
        )
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('balance')), 0)

        # ---------------------------------------------------------------------
        # Edit move6, receive less: 2 in negative stock
        # ---------------------------------------------------------------------
        self._set_quantity(move6, 8)
        self._close()
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('balance')), -24)

        # -----------------------------------------------------------
        # receive 4 to counterbalance now
        # -----------------------------------------------------------
        self._make_in_move(self.product1, 4, 15)
        self._close()
        self.assertEqual(self.product1.total_value, 30)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('balance')), 30)

    def test_fifo_perpetual_2(self):
        """ Normal fifo flow (no negative handling) """
        # http://accountingexplained.com/financial/inventories/fifo-method
        self.product1.categ_id.property_cost_method = 'fifo'

        # Beginning Inventory: 68 units @ 15.00 per unit
        move1 = self._make_in_move(self.product1, 68, 15)

        self.assertEqual(move1.value, 1020.0)

        self.assertEqual(move1.remaining_qty, 68.0)

        # Purchase 140 units @ 15.50 per unit
        move2 = self._make_in_move(self.product1, 140, 15.5)

        self.assertEqual(move2.value, 2170.0)

        self.assertEqual(move1.remaining_qty, 68.0)
        self.assertEqual(move2.remaining_qty, 140.0)

        # Sale 94 units @ 19.00 per unit
        move3 = self._make_out_move(self.product1, 94)

        # note: it' ll have to get 68 units from the first batch and 26 from the second one
        # so its value should be -((68*15) + (26*15.5)) = -1423
        self.assertEqual(move3.value, 1423.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 114)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out moves

        # Purchase 40 units @ 16.00 per unit
        move4 = self._make_in_move(self.product1, 40, 16)

        self.assertEqual(move4.value, 640.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 114)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.remaining_qty, 40.0)

        # Purchase 78 units @ 16.50 per unit
        move5 = self._make_in_move(self.product1, 78, 16.5)

        self.assertEqual(move5.value, 1287.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 114)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.remaining_qty, 40.0)
        self.assertEqual(move5.remaining_qty, 78.0)

        # Sale 116 units @ 19.50 per unit
        move6 = self._make_out_move(self.product1, 116)

        # note: it' ll have to get 114 units from the move2 and 2 from move4
        # so its value should be -((114*15.5) + (2*16)) = 1735
        self.assertEqual(move6.value, 1799.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 0)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.remaining_qty, 38.0)
        self.assertEqual(move5.remaining_qty, 78.0)
        self.assertEqual(move6.remaining_qty, 0.0)  # unused in out moves

        # Sale 62 units @ 21 per unit
        move7 = self._make_out_move(self.product1, 62)

        # note: it' ll have to get 38 units from the move4 and 24 from move5
        # so its value should be -((38*16) + (24*16.5)) = 608 + 396
        self.assertEqual(move7.value, 1004.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 0)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.remaining_qty, 0.0)
        self.assertEqual(move5.remaining_qty, 54.0)
        self.assertEqual(move6.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move7.remaining_qty, 0.0)  # unused in out moves

        # send 10 units in our transit location, the valorisation should not be impacted
        transit_location = self.env['stock.location'].search([
            ('company_id', '=', self.company.id),
            ('usage', '=', 'transit'),
            ('active', '=', False)
        ], limit=1)
        transit_location.active = True
        move8 = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': transit_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move8._action_confirm()
        move8._action_assign()
        move8.move_line_ids.quantity = 10.0
        move8.picked = True
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
        move9 = self._make_out_move(self.product1, 10)

        # note: it' ll have to get 10 units from move5 so its value should
        # be -(10*16.50) = -165
        self.assertEqual(move9.value, 165.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 0)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.remaining_qty, 0.0)
        self.assertEqual(move5.remaining_qty, 44.0)
        self.assertEqual(move6.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move7.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move8.remaining_qty, 0.0)  # unused in internal moves
        self.assertEqual(move9.remaining_qty, 0.0)  # unused in out moves

    def test_fifo_negative_1(self):
        """ Send products that you do not have. Value the first outgoing move to the standard
        price, receive in multiple times the delivered quantity and run _fifo_vacuum to compensate.
        """
        self.product1.categ_id.property_cost_method = 'fifo'

        # We expect the user to set manually set a standard price to its products if its first
        # transfer is sending products that he doesn't have.
        with freeze_time(Datetime.now() - timedelta(seconds=1)):
            self.product1.product_tmpl_id.standard_price = 8.0

        # ---------------------------------------------------------------------
        # Send 50 units you don't have
        # ---------------------------------------------------------------------
        move1 = self._make_out_move(self.product1, 50)

        # stock values for move1
        self.assertEqual(move1.value, 400.0)
        self.assertEqual(move1.remaining_qty, 0.0)  # normally unused in out moves, but as it moved negative stock we mark it

        closing_move = self._close()
        valuation_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.stock_valuation_account)
        expense_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.expense_account)
        self.assertRecordValues(
            valuation_aml + expense_aml,
            [
                {'account_id': self.stock_valuation_account.id, 'debit': 0, 'credit': 400},
                {'account_id': self.expense_account.id, 'debit': 400, 'credit': 0},
            ]
        )

        # ---------------------------------------------------------------------
        # Receive 40 units @ 15
        # ---------------------------------------------------------------------
        move2 = self._make_in_move(self.product1, 40, 15)

        # stock values for move2
        self.assertEqual(move2.value, 600.0)
        self.assertEqual(move2.remaining_qty, 0)

        # ---------------------------------------------------------------------
        # The vacuum ran
        # ---------------------------------------------------------------------

        closing_move = self._close()
        valuation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.stock_valuation_account
        )
        expense_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.expense_account
        )
        self.assertRecordValues(
            valuation_aml + expense_aml,
            [
                {"account_id": self.stock_valuation_account.id, "debit": 250, "credit": 0},
                {"account_id": self.expense_account.id, "debit": 0, "credit": 250},
            ],
        )

        # ---------------------------------------------------------------------
        # Receive 20 units @ 25
        # ---------------------------------------------------------------------
        self._make_in_move(self.product1, 20, 25)

        # ---------------------------------------------------------------------
        # The vacuum ran
        # ---------------------------------------------------------------------

        closing_move = self._close()
        valuation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.stock_valuation_account
        )
        expense_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.expense_account
        )
        self.assertRecordValues(
            valuation_aml + expense_aml,
            [
                {"account_id": self.stock_valuation_account.id, "debit": 400, "credit": 0},
                {"account_id": self.expense_account.id, "debit": 0, "credit": 400},
            ],
        )

        # ---------------------------------------------------------------------
        # Ending
        # ---------------------------------------------------------------------
        self.assertEqual(self.product1.qty_available, 10)
        self.assertEqual(self.product1.total_value, 250)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('balance')), 250)
        self.assertEqual(sum(self._get_expense_move_lines().mapped('balance')), -250)

    def test_fifo_negative_2(self):
        """ Receives 10 units, send 10 units, then send more: the extra quantity should be valued
        at the last fifo price, running the vacuum should not do anything.
        """
        self.product1.categ_id.property_cost_method = 'fifo'

        # ---------------------------------------------------------------------
        # Receive 10@10
        # ---------------------------------------------------------------------
        move1 = self._make_in_move(self.product1, 10, 10)

        # stock values for move1
        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_qty, 10.0)

        # ---------------------------------------------------------------------
        # Send 10
        # ---------------------------------------------------------------------
        move2 = self._make_out_move(self.product1, 10, 10)

        # stock values for move2
        self.assertEqual(move2.value, 100.0)
        self.assertEqual(move1.remaining_qty, 0.0)

        with self.assertRaises(UserError):
            self._close()

        # ---------------------------------------------------------------------
        # Send 21
        # ---------------------------------------------------------------------
        move3 = self._make_out_move(self.product1, 21)

        # stock values for move3
        self.assertEqual(move3.value, 210.0)

        # account values for move3
        closing_move = self._close()
        valuation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.stock_valuation_account
        )
        expense_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.expense_account
        )
        self.assertRecordValues(
            valuation_aml + expense_aml,
            [
                {"account_id": self.stock_valuation_account.id, "debit": 0, "credit": 210},
                {"account_id": self.expense_account.id, "debit": 210, "credit": 0},
            ],
        )

        # ---------------------------------------------------------------------
        # Ending
        # ---------------------------------------------------------------------
        self.assertEqual(self.product1.qty_available, -21)
        self.assertEqual(self.product1.total_value, -210)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('balance')), -210)

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
        move1 = self._make_in_move(self.product1, 10, 10, create_picking=True)
        receipt = move1.picking_id

        # stock values for move1
        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_qty, 10.0)
        self.assertEqual(move1.price_unit, 10.0)

        # ---------------------------------------------------------------------
        # Add a stock move, receive 10@20 of another product
        # ---------------------------------------------------------------------
        self.product2.categ_id.property_cost_method = 'fifo'
        self.product2.standard_price = 20
        move2 = self.env['stock.move'].create({
            'picking_id': receipt.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'value_manual': 200.0,
            'move_line_ids': [(0, 0, {
                'product_id': self.product2.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_id': self.uom_unit.id,
                'quantity': 10.0,
            })]
        })
        # Move is automatically set to Done as it is linked to a Done picking
        self.assertEqual(move2.state, 'done')
        self.assertEqual(move2.value, 200.0)
        self.assertEqual(move2.remaining_qty, 10.0)
        self.assertEqual(self.product2.standard_price, 20.0)

        self.assertEqual(self.product1.qty_available, 10)
        self.assertEqual(self.product1.total_value, 100)
        self.assertEqual(self.product2.qty_available, 10)
        self.assertEqual(self.product2.total_value, 200)

        closing_move = self.env['account.move'].browse(move2.company_id.action_close_stock_valuation()['res_id'])
        valuation_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.stock_valuation_account)
        expense_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.expense_account)
        self.assertRecordValues(
            valuation_aml + expense_aml,
            [
                {'account_id': self.stock_valuation_account.id, 'debit': 300, 'credit': 0},
                {'account_id': self.expense_account.id, 'debit': 0, 'credit': 300},
            ]
        )

        # ---------------------------------------------------------------------
        # Edit the previous stock move, receive 11
        # ---------------------------------------------------------------------
        self._set_quantity(move2, 11)

        self.assertEqual(move2.value, 220.0)  # after correction, the move should be valued at 11@20
        self.assertEqual(move2.quantity, 11.0)
        self.product2._invalidate_cache()
        self.product2.standard_price = 20.0

        closing_move = self.env['account.move'].browse(move2.company_id.action_close_stock_valuation()['res_id'])
        valuation_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.stock_valuation_account)
        expense_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.expense_account)
        self.assertRecordValues(
            valuation_aml + expense_aml,
            [
                {'account_id': self.stock_valuation_account.id, 'debit': 320, 'credit': 0},
                {'account_id': self.expense_account.id, 'debit': 0, 'credit': 320},
            ]
        )

        # ---------------------------------------------------------------------
        # Send 11 product 2
        # ---------------------------------------------------------------------
        move3 = self._make_out_move(self.product2, 11, create_picking=True)

        self.assertEqual(move3.value, 220.0)
        self.assertEqual(move3.remaining_qty, 0.0)
        self.assertEqual(self.product2.standard_price, 20.0)
        self.assertEqual(self.product2.qty_available, 0)
        self.product2._invalidate_cache()
        self.product2.standard_price = 20.0

        closing_move = self.env['account.move'].browse(move2.company_id.action_close_stock_valuation()['res_id'])
        valuation_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.stock_valuation_account)
        expense_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.expense_account)
        self.assertRecordValues(
            valuation_aml + expense_aml,
            [
                {'account_id': self.stock_valuation_account.id, 'debit': 100, 'credit': 0},
                {'account_id': self.expense_account.id, 'debit': 0, 'credit': 100},
            ]
        )

    def test_fifo_add_moveline_in_done_move_1(self):
        self.product1.categ_id.property_cost_method = 'fifo'

        # ---------------------------------------------------------------------
        # Receive 10@10
        # ---------------------------------------------------------------------
        move1 = self._make_in_move(self.product1, 10, 10)

        # stock values for move1
        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_qty, 10.0)
        self.assertEqual(move1.price_unit, 10.0)

        # ---------------------------------------------------------------------
        # Add a new move line to receive 10 more
        # ---------------------------------------------------------------------
        self.assertEqual(len(move1.move_line_ids), 1)
        self._set_quantity(move1, 20)
        self.assertEqual(move1.value, 200.0)
        self.assertEqual(move1.remaining_qty, 20.0)
        self.assertEqual(len(move1.move_line_ids), 2)

        self.assertEqual(self.product1.qty_available, 20)
        self.assertEqual(self.product1.total_value, 200)

        closing_move = self.env['account.move'].browse(move1.company_id.action_close_stock_valuation()['res_id'])
        credit_line = closing_move.line_ids.filtered(lambda l: l.credit > 0)
        self.assertEqual(len(credit_line), 1)
        self.assertEqual(credit_line.debit, 0.0)
        self.assertEqual(credit_line.credit, 200.0)

        debit_line = closing_move.line_ids.filtered(lambda l: l.debit > 0)
        self.assertEqual(len(debit_line), 1)
        self.assertEqual(debit_line.debit, 200.0)
        self.assertEqual(debit_line.credit, 0.0)

    def test_fifo_edit_done_move1(self):
        """ Increase OUT done move while quantities are available.
        """
        self.product1.categ_id.property_cost_method = 'fifo'

        # ---------------------------------------------------------------------
        # Receive 10@10
        # ---------------------------------------------------------------------
        move1 = self._make_in_move(self.product1, 10, 10)

        # stock values for move1
        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_qty, 10.0)
        self.assertAlmostEqual(self.product1.qty_available, 10.0)
        self.assertEqual(self.product1.total_value, 100)

        closing_move = self._close()
        expense_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.expense_account)
        valuation_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.stock_valuation_account)
        self.assertRecordValues(
            valuation_aml + expense_aml,
            [
                {'account_id': self.stock_valuation_account.id, 'debit': 100, 'credit': 0},
                {'account_id': self.expense_account.id, 'debit': 0, 'credit': 100},
            ]
        )

        # ---------------------------------------------------------------------
        # Receive 10@12
        # ---------------------------------------------------------------------
        move2 = self._make_in_move(self.product1, 10, 12)

        # stock values for move2
        self.assertEqual(move2.value, 120.0)
        self.assertEqual(move2.remaining_qty, 10.0)
        self.assertEqual(move2._get_price_unit(), 12.0)
        self.assertAlmostEqual(self.product1.qty_available, 20.0)
        self.assertAlmostEqual(self.product1.qty_available, 20.0)
        self.assertEqual(self.product1.total_value, 220)

        closing_move = self._close()
        expense_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.expense_account)
        valuation_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.stock_valuation_account)
        self.assertRecordValues(
            valuation_aml + expense_aml,
            [
                {"account_id": self.stock_valuation_account.id, "debit": 120, "credit": 0},
                {"account_id": self.expense_account.id, "debit": 0, "credit": 120},
            ],
        )

        # ---------------------------------------------------------------------
        # Send 8
        # ---------------------------------------------------------------------
        move3 = self._make_out_move(self.product1, 8)

        # stock values for move3
        self.assertEqual(move3.value, 80.0)
        self.assertEqual(move3.remaining_qty, 0.0)
        self.assertAlmostEqual(self.product1.qty_available, 12.0)
        self.assertAlmostEqual(self.product1.qty_available, 12.0)
        self.assertEqual(self.product1.total_value, 140)
        closing_move = self._close()
        expense_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.expense_account)
        valuation_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.stock_valuation_account)
        self.assertRecordValues(
            valuation_aml + expense_aml,
            [
                {"account_id": self.stock_valuation_account.id, "debit": 0, "credit": 80},
                {"account_id": self.expense_account.id, "debit": 80, "credit": 0},
            ],
        )

        # ---------------------------------------------------------------------
        # Edit last move, send 14 instead
        # it should use a ration of old value and set the correct value at closing²
        # ---------------------------------------------------------------------
        move3.quantity = 14
        self.assertEqual(move3.product_qty, 8)
        # old value: -80 -(8@10)
        # real value: -148 => -(10@10 + 4@12)
        # estimated value: -140 => -(14@10)
        self.assertEqual(move3.value, 140)

        self.assertEqual(self.product1.total_value, 72)
        closing_move = self._close()
        expense_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.expense_account)
        valuation_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.stock_valuation_account)
        # The closing is correct despite an incorrect out move value
        self.assertRecordValues(
            valuation_aml + expense_aml,
            [
                {"account_id": self.stock_valuation_account.id, "debit": 0, "credit": 68},
                {"account_id": self.expense_account.id, "debit": 68, "credit": 0},
            ],
        )

        # ---------------------------------------------------------------------
        # Ending
        # ---------------------------------------------------------------------
        self.assertEqual(self.product1.qty_available, 6)
        self.assertAlmostEqual(self.product1.qty_available, 6.0)
        self.assertEqual(self.product1.total_value, 72)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('balance')), 72)

    def test_fifo_edit_done_move2(self):
        """ Decrease, then increase OUT done move while quantities are available.
        """
        self.product1.categ_id.property_cost_method = 'fifo'

        # ---------------------------------------------------------------------
        # Receive 10@10
        # ---------------------------------------------------------------------
        move1 = self._make_in_move(self.product1, 10, 10)

        # stock values for move1
        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_qty, 10.0)

        # ---------------------------------------------------------------------
        # Send 10
        # ---------------------------------------------------------------------
        move2 = self._make_out_move(self.product1, 10)

        # stock values for move2
        self.assertEqual(move2.value, 100.0)
        self.assertEqual(move2.remaining_qty, 0.0)

        # ---------------------------------------------------------------------
        # Actually, send 8 in the last move
        # ---------------------------------------------------------------------
        move2.quantity = 8

        self.assertEqual(move2.value, 80.0)  # the move actually sent 8@10

        self.assertEqual(self.product1.qty_available, 2)

        # ---------------------------------------------------------------------
        # Actually, send 10 in the last move
        # ---------------------------------------------------------------------
        move2.quantity = 10

        self.assertEqual(move2.value, 100.0)  # the move actually sent 10@10
        self.assertEqual(self.product1.qty_available, 0)
        self.assertEqual(self.product1.total_value, 0)

    def test_fifo_standard_price_upate_1(self):
        product = self.env['product.product'].create({
            'name': 'product1',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_goods').id,
        })
        product.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self._make_in_move(product, 3, unit_cost=17)
        self._make_in_move(product, 1, unit_cost=23)
        self.assertEqual(product.standard_price, 18.5)
        self._make_out_move(product, 3)
        self.assertEqual(product.standard_price, 23)

    def test_fifo_standard_price_upate_2(self):
        product = self.env['product.product'].create({
            'name': 'product1',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_goods').id,
        })
        product.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self._make_in_move(product, 5, unit_cost=17)
        self._make_in_move(product, 1, unit_cost=23)
        self.assertEqual(product.standard_price, 18)
        self._make_out_move(product, 4)
        self.assertEqual(product.standard_price, 20)

    def test_fifo_standard_price_upate_3(self):
        """Standard price must be set on move in if no product and if first move."""
        product = self.env['product.product'].create({
            'name': 'product1',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_goods').id,
        })
        product.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self._make_in_move(product, 5, unit_cost=17)
        self._make_in_move(product, 1, unit_cost=23)
        self.assertEqual(product.standard_price, 18)
        self._make_out_move(product, 4)
        self.assertEqual(product.standard_price, 20)
        self._make_out_move(product, 1)
        self.assertEqual(product.standard_price, 23)
        self._make_out_move(product, 1)
        self.assertEqual(product.standard_price, 23)
        self._make_in_move(product, 1, unit_cost=77)
        self.assertEqual(product.standard_price, 77)

    def test_create_done_move(self):
        """Stock Move created directly in Done state must impact de valuation."""
        self.product1.categ_id.property_cost_method = 'average'
        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 8.0,
            'price_unit': 1,
            'state': 'done',
            'move_line_ids': [(0, 0, {
                'product_id': self.product1.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_id': self.uom_unit.id,
                'quantity': 8.0,
                'state': 'done',
            })]
        })
        move1.value_manual = 8.0
        self.assertEqual(self.product1.qty_available, 8.0)
        self.assertEqual(self.product1.total_value, 8.0)

    def test_average_perpetual_1(self):
        # http://accountingexplained.com/financial/inventories/avco-method
        self.product1.categ_id.property_cost_method = 'average'

        # Beginning Inventory: 60 units @ 15.00 per unit
        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 60.0,
            'price_unit': 15,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 60.0
        move1.picked = True
        move1._action_done()
        move1.value_manual = 900

        self.assertEqual(move1.value, 900.0)

        # Purchase 140 units @ 15.50 per unit
        move2 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 140.0,
            'price_unit': 15.50,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 140.0
        move2.picked = True
        move2._action_done()
        move2.value_manual = 2170

        self.assertEqual(move2.value, 2170.0)

        # Sale 190 units @ 15.35 per unit
        move3 = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 190.0,
        })
        move3._action_confirm()
        move3._action_assign()
        move3.move_line_ids.quantity = 190.0
        move3.picked = True
        move3._action_done()

        self.assertEqual(move3.value, 2916.5)

        # Purchase 70 units @ $16.00 per unit
        move4 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 70.0,
            'price_unit': 16.00,
        })
        move4._action_confirm()
        move4._action_assign()
        move4.move_line_ids.quantity = 70.0
        move4.picked = True
        move4._action_done()
        move4.value_manual = 1120

        self.assertEqual(move4.value, 1120.0)

        # Sale 30 units @ $19.50 per unit
        move5 = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 30.0,
        })
        move5._action_confirm()
        move5._action_assign()
        move5.move_line_ids.quantity = 30.0
        move5.picked = True
        move5._action_done()

        self.assertEqual(move5.value, 477.60)

        # Receives 10 units but assign them to an owner, the valuation should not be impacted.
        move6 = self.env['stock.move'].create({
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
        move6.move_line_ids.quantity = 10.0
        move6.picked = True
        move6._action_done()
        move6.value_manual = 990

        self.assertEqual(move6.value, 0)

        # Sale 50 units @ $19.50 per unit (no stock anymore)
        move7 = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 50.0,
        })
        move7._action_confirm()
        move7._action_assign()
        move7.move_line_ids.quantity = 50.0
        move7.picked = True
        move7._action_done()

        self.assertEqual(move7.value, 796.0)
        self.assertAlmostEqual(self.product1.qty_available, 10)
        self.assertAlmostEqual(self.product1.total_value, 0.0)

    def test_average_perpetual_2(self):
        self.product1.categ_id.property_cost_method = 'average'
        self._make_in_move(self.product1, 10, 10)
        self.assertEqual(self.product1.standard_price, 10)

        move2 = self._make_in_move(self.product1, 10, 15)
        self.assertEqual(self.product1.standard_price, 12.5)

        self._make_out_move(self.product1, 15)
        self.assertEqual(self.product1.standard_price, 12.5)

        self._make_out_move(self.product1, 10)
        # note: 5 units were sent estimated at 12.5 (negative stock)
        self.assertEqual(self.product1.standard_price, 12.5)
        self.assertEqual(self.product1.qty_available, -5)
        self.assertEqual(self.product1.total_value, -62.5)

        self._set_quantity(move2, 20)

        self.assertEqual(self.product1.qty_available, 5)
        self.assertEqual(self.product1.total_value, 66.67)
        self.assertEqual(self.product1.standard_price, 13.33)

    def test_average_perpetual_3(self):
        self.product1.categ_id.property_cost_method = 'average'

        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 10.0
        move1.picked = True
        move1._action_done()
        move1.value_manual = 100.0

        self.assertEqual(self.product1.qty_available, 10.0)
        self.assertEqual(self.product1.total_value, 100.0)
        self.product1._invalidate_cache()

        move2 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 15,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 10.0
        move2.picked = True
        move2._action_done()
        move2.value_manual = 150.0

        self.assertEqual(self.product1.qty_available, 20.0)
        self.assertEqual(self.product1.total_value, 250.0)
        self.product1._invalidate_cache()

        move3 = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 15.0,
        })
        move3._action_confirm()
        move3._action_assign()
        move3.move_line_ids.quantity = 15.0
        move3.picked = True
        move3._action_done()

        self.assertEqual(self.product1.qty_available, 5.0)
        self.assertEqual(self.product1.total_value, 62.5)
        self.product1._invalidate_cache()

        move4 = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move4._action_confirm()
        move4._action_assign()
        move4.move_line_ids.quantity = 10.0
        move4.picked = True
        move4._action_done()

        self.assertEqual(self.product1.qty_available, -5.0)
        self.assertEqual(self.product1.total_value, -62.5)
        self.product1._invalidate_cache()

        move2.move_line_ids.quantity = 0
        self.assertEqual(self.product1.qty_available, -15.0)

    def test_average_perpetual_4(self):
        """receive 1@10, receive 1@5 insteadof 3@5"""
        self.product1.categ_id.property_cost_method = 'average'

        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 1.0
        move1.picked = True
        move1._action_done()
        move1.value_manual = 10.0

        move2 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 3.0,
            'price_unit': 5,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 1.0
        move2.picked = True
        move2._action_done()
        move2.value_manual = 5.0

        self.assertAlmostEqual(self.product1.qty_available, 2.0)
        self.assertAlmostEqual(self.product1.standard_price, 7.5)

    def test_average_perpetual_5(self):
        ''' Set owner on incoming move => no valuation '''
        self.product1.categ_id.property_cost_method = 'average'

        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 1.0
        move1.move_line_ids.owner_id = self.owner1.id
        move1.picked = True
        move1._action_done()
        move1.value_manual = 10.0

        self.assertAlmostEqual(move1.remaining_qty, 0.0)
        self.assertAlmostEqual(self.product1.qty_available, 1.0)
        self.assertAlmostEqual(self.product1.total_value, 0.0)

    def test_average_perpetual_6(self):
        """ Batch validation of moves """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'

        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 1.0
        move1.picked = True

        move2 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'price_unit': 5,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 1.0
        move2.picked = True

        # Receive both at the same time
        (move1 | move2)._action_done()
        move1.value_manual = 10.0
        move2.value_manual = 5.0

        self.assertAlmostEqual(self.product1.standard_price, 7.5)
        self.assertEqual(self.product1.qty_available, 2)
        self.assertEqual(self.product1.total_value, 15)

    def test_average_perpetual_7(self):
        """ Test edit in the past. Receive 5@10, receive 10@20, edit the first move to receive
        15 instead.
        """
        self.product1.categ_id.property_cost_method = 'average'

        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1.quantity = 5
        move1.picked = True
        move1._action_done()
        move1.value_manual = 50.0

        self.assertAlmostEqual(self.product1.standard_price, 10)
        self.assertAlmostEqual(move1.value, 50)
        self.assertAlmostEqual(self.product1.qty_available, 5)
        self.assertAlmostEqual(self.product1.total_value, 50)
        self.product1._invalidate_cache()

        move2 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10,
            'price_unit': 20,
        })
        move2._action_confirm()
        move2.quantity = 10
        move2.picked = True
        move2._action_done()
        move2.value_manual = 200.0

        self.assertAlmostEqual(self.product1.standard_price, 16.67)
        self.assertAlmostEqual(move2.value, 200)
        self.assertAlmostEqual(self.product1.qty_available, 15)
        self.assertAlmostEqual(self.product1.total_value, 250)
        self.product1._invalidate_cache()

        self._set_quantity(move1, 15)

        self.assertAlmostEqual(self.product1.standard_price, 14.0)
        self.assertAlmostEqual(self.product1.qty_available, 25)
        self.assertAlmostEqual(self.product1.total_value, 350)

    def test_average_perpetual_8(self):
        """ Receive 1@10, then dropship 1@20, finally return the dropship. Dropship should not
            impact the price.
        """
        self.product1.categ_id.property_cost_method = 'average'

        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1.quantity = 1
        move1.picked = True
        move1._action_done()
        move1.value_manual = 10.0

        self.assertAlmostEqual(self.product1.standard_price, 10)

        move2 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'price_unit': 20,
        })
        move2._action_confirm()
        move2.quantity = 1
        move2.picked = True
        move2._action_done()

        self.assertAlmostEqual(self.product1.standard_price, 10.0)

        move3 = self.env['stock.move'].create({
            'location_id': self.customer_location.id,
            'location_dest_id': self.supplier_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'price_unit': 20,
        })
        move3._action_confirm()
        move3.quantity = 1
        move3.picked = True
        move3._action_done()

        self.assertAlmostEqual(self.product1.standard_price, 10.0)

    def test_average_perpetual_9(self):
        """ When a product has an available quantity of -5, edit an incoming shipment and increase
        the received quantity by 5 units.
        """
        self.product1.categ_id.property_cost_method = 'average'
        # receive 10
        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1.picked = True
        move1._action_done()
        move1.value_manual = 100.0

        # deliver 15
        move2 = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 15.0,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 15.0
        move2.picked = True
        move2._action_done()

        # increase the receipt to 15
        move1.move_line_ids.quantity = 15

    def test_average_stock_user(self):
        """ deliver an average product as a stock user. """
        self.product1.categ_id.property_cost_method = 'average'
        # receive 10
        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1.picked = True
        move1._action_done()

        # sell 15
        move2 = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 15.0,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 15.0
        move2.picked = True
        move2.with_user(self.inventory_user)._action_done()

    def test_average_negative_1(self):
        """ Test edit in the past. Receive 10, send 20, edit the second move to only send 10."""
        self.product1.categ_id.property_cost_method = 'average'

        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 10.0
        move1.picked = True
        move1._action_done()
        move1.value_manual = 100.0

        self._create_invoice('in_invoice', self.product1, 10, 10)

        move2 = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 20.0,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 20.0
        move2.picked = True
        move2._action_done()

        self._create_invoice('out_invoice', self.product1, 20, 10)
        valuation_aml = self._get_stock_valuation_move_lines()
        move2_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 2)
        self.assertEqual(move2_valuation_aml.debit, 0)
        self.assertEqual(move2_valuation_aml.credit, 200)

        self._set_quantity(move2, 10.0)
        self._create_invoice('in_invoice', self.product1, 10, 10)

        valuation_aml = self._get_stock_valuation_move_lines()
        move2_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 3)
        self.assertEqual(move2_valuation_aml.debit, 100)
        self.assertEqual(move2_valuation_aml.credit, 0)

        self._set_quantity(move2, 11.0)
        self._create_invoice('out_invoice', self.product1, 1, 10)

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
        move1 = self._make_out_move(self.product1, 10, force_assign=True)
        self.assertEqual(move1.value, 990)
        self.assertEqual(self.product1.qty_available, -10)
        self.assertEqual(self.product1.total_value, -990.0)

    def test_average_negative_3(self):
        """ Send goods that you don't have in stock but received and send some units before.
        """
        self.product1.categ_id.property_cost_method= 'average'

        # set a standard price
        self.product1.standard_price = 99

        # Receives 10 produts at 10
        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 10.0
        move1.picked = True
        move1._action_done()
        move1.value_manual = 100

        self.assertEqual(move1.value, 100)
        self.assertEqual(self.product1.qty_available, 10)
        self.assertEqual(self.product1.total_value, 100)

        # send 10 products
        move2 = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 10.0
        move2.picked = True
        move2._action_done()

        self.assertEqual(move2.value, 100.0)
        self.assertEqual(move2.remaining_qty, 0.0)  # unused in average move
        self.product1._invalidate_cache()

        # send 10 products again
        move3 = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move3._action_confirm()
        move3.quantity = 10.0
        move3.picked = True
        move3._action_done()

        self.assertEqual(move3.value, 0.0)

    def test_average_negative_4(self):
        self.product1.categ_id.property_cost_method = 'average'

        # set a standard price
        self.product1.standard_price = 99

        # Receives 10 produts at 10
        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 10.0
        move1.picked = True
        move1._action_done()
        move1.value_manual = 100.0

        self.assertEqual(move1.value, 100.0)

    def test_average_negative_5(self):
        self.product1.categ_id.property_cost_method = 'average'

        # in 10 @ 10
        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 10.0
        move1.picked = True
        move1._action_done()
        move1.value_manual = 100.0

        self.assertEqual(move1.value, 100.0)
        self.assertEqual(self.product1.standard_price, 10)

        # in 10 @ 20
        move2 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 20,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 10.0
        move2.picked = True
        move2._action_done()
        move2.value_manual = 200.0

        self.assertEqual(move2.value, 200.0)
        self.assertEqual(self.product1.standard_price, 15)

        # send 5
        move3 = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })
        move3._action_confirm()
        move3.quantity = 5.0
        move3.picked = True
        move3._action_done()

        self.assertEqual(move3.value, 75.0)
        self.assertEqual(self.product1.standard_price, 15)

        # send 30
        move4 = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 30.0,
        })
        move4._action_confirm()
        move4.quantity = 30.0
        move4.picked = True
        move4._action_done()

        self.assertEqual(move4.value, 450.0)
        self.assertEqual(self.product1.standard_price, 15)

        # in 20 @ 20
        move5 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 20.0,
            'price_unit': 20,
        })
        move5._action_confirm()
        move5._action_assign()
        move5.move_line_ids.quantity = 20.0
        move5.picked = True
        move5._action_done()
        move5.value_manual = 400.0
        self.assertEqual(move5.value, 400.0)

        # Move 4 is now fixed, it initially sent 30@15 but the 5 last units were negative and estimated
        # at 15 (1125). The new receipt made these 5 units sent at 20 (1500), so a 450 value is added
        # to move4.
        self.assertEqual(move4.value, 450)

        # So we have 5@20 in stock.
        self.assertEqual(self.product1.qty_available, 5)
        self.assertEqual(self.product1.total_value, 100)
        self.assertEqual(self.product1.standard_price, 20)

        # send 5 products to empty the inventory, the average price should not go to 0
        move6 = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })
        move6._action_confirm()
        move6.quantity = 5.0
        move6.picked = True
        move6._action_done()

        self.assertEqual(move6.value, 100.0)
        self.assertEqual(self.product1.standard_price, 20)

        # in 10 @ 10, the new average price should be 10
        move7 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
            'price_unit': 10,
        })
        move7._action_confirm()
        move7._action_assign()
        move7.move_line_ids.quantity = 10.0
        move7.picked = True
        move7._action_done()
        move7.value_manual = 100.0

        self.assertEqual(move7.value, 100.0)
        self.assertEqual(self.product1.standard_price, 10)

    def test_average_automated_with_cost_change(self):
        """ Test of the handling of a cost change with a negative stock quantity with FIFO+AVCO costing method"""
        self.product1.categ_id.property_cost_method = 'average'
        self.product1.categ_id.property_valuation = 'real_time'

        # Step 1: Sell (and confirm) 10 units we don't have @ 100
        self.product1.standard_price = 100
        move1 = self._make_out_move(self.product1, 10, force_assign=True)

        self.assertAlmostEqual(self.product1.qty_available, -10.0)
        self.assertEqual(move1.value, 1000.0)
        self.assertAlmostEqual(self.product1.total_value, -1000.0)

        # Step2: Change product cost from 100 to 10 -> Nothing should appear in inventory
        # valuation as the quantity is negative
        self.product1.standard_price = 10
        self.assertEqual(self.product1.total_value, -100.0)

        # Step 3: Make an inventory adjustment to set to total counted value at 0 -> Inventory
        # valuation should be at 0 with a compensation layer at 900 (1000 - 100)
        inventory_location = self.product1.property_stock_inventory
        inventory_location.company_id = self.env.company.id

        move2 = self.env['stock.move'].create({
            'location_id': inventory_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 10.0
        move2.picked = True
        move2._action_done()

        # Check if the move adjustment has correctly been done
        self.assertAlmostEqual(self.product1.qty_available, 0.0)
        self.assertAlmostEqual(move2.value, 100.0)

        # Check if the compensation layer is as expected, with final inventory value being 0
        self.assertAlmostEqual(self.product1.total_value, 0.0)

    def test_average_manual_1(self):
        ''' Set owner on incoming move => no valuation '''
        self.product1.categ_id.property_cost_method = 'average'
        self.product1.categ_id.property_valuation = 'periodic'

        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 1.0
        move1.move_line_ids.owner_id = self.owner1.id
        move1.picked = True
        move1._action_done()

        self.assertAlmostEqual(move1.remaining_qty, 0.0)
        self.assertAlmostEqual(self.product1.qty_available, 1.0)
        self.assertAlmostEqual(self.product1.total_value, 0.0)

    def test_standard_perpetual_1(self):
        ''' Set owner on incoming move => no valuation '''
        self.product1.categ_id.property_cost_method = 'standard'

        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 1.0
        move1.move_line_ids.owner_id = self.owner1.id
        move1.picked = True
        move1._action_done()

        self.assertAlmostEqual(move1.remaining_qty, 0.0)
        self.assertAlmostEqual(self.product1.qty_available, 1.0)
        self.assertAlmostEqual(self.product1.total_value, 0.0)

    def test_standard_manual_1(self):
        ''' Set owner on incoming move => no valuation '''
        self.product1.categ_id.property_cost_method = 'standard'
        self.product1.categ_id.property_valuation = 'periodic'

        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'price_unit': 10,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 1.0
        move1.move_line_ids.owner_id = self.owner1.id
        move1.picked = True
        move1._action_done()

        self.assertAlmostEqual(move1.remaining_qty, 0.0)
        self.assertAlmostEqual(self.product1.qty_available, 1.0)
        self.assertAlmostEqual(self.product1.total_value, 0.0)

    def test_standard_manual_2(self):
        """Validate a receipt as a regular stock user."""
        self.product1.categ_id.property_cost_method = 'standard'
        self.product1.categ_id.property_valuation = 'periodic'

        self.product1.standard_price = 10.0

        move1 = self.env['stock.move'].with_user(self.inventory_user).create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 10.0
        move1.picked = True
        move1._action_done()

    def test_standard_perpetual_2(self):
        """Validate a receipt as a regular stock user."""
        self.product1.categ_id.property_cost_method = 'standard'
        self.product1.categ_id.property_valuation = 'real_time'

        self.product1.standard_price = 10.0

        move1 = self.env['stock.move'].with_user(self.inventory_user).create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 10.0
        move1.picked = True
        move1._action_done()

    def test_change_cost_method_1(self):
        """ Change the cost method from FIFO to AVCO.
        """
        # ---------------------------------------------------------------------
        # Use FIFO, make some operations
        # ---------------------------------------------------------------------
        self.product1.categ_id.property_cost_method = 'fifo'

        # receive 10@10
        self._make_in_move(self.product1, 10, 10)

        # receive 10@15
        self._make_in_move(self.product1, 10, 15)

        # sell 1
        self._make_out_move(self.product1, 1)

        self.assertAlmostEqual(self.product1.qty_available, 19)
        self.assertEqual(self.product1.total_value, 240)

        # ---------------------------------------------------------------------
        # Change the production valuation to AVCO
        # ---------------------------------------------------------------------
        self.product1.categ_id.property_cost_method = 'average'

        # valuation should stay to ~240
        self.assertAlmostEqual(self.product1.qty_available, 19)
        self.assertAlmostEqual(self.product1.total_value, 237.5)

        self.assertEqual(self.product1.standard_price, 12.5)

    def test_change_cost_method_2(self):
        """ Change the cost method from FIFO to standard.
        """
        # ---------------------------------------------------------------------
        # Use FIFO, make some operations
        # ---------------------------------------------------------------------
        self.product1.categ_id.property_cost_method = 'fifo'

        # receive 10@10
        self._make_in_move(self.product1, 10, 10)

        # receive 10@15
        self._make_in_move(self.product1, 10, 15)

        # sell 1
        self._make_out_move(self.product1, 1)

        self.assertAlmostEqual(self.product1.qty_available, 19)
        self.assertEqual(self.product1.total_value, 240)

        # ---------------------------------------------------------------------
        # Change the production valuation to Standard
        # ---------------------------------------------------------------------
        self.product1.categ_id.property_cost_method = 'standard'

        # valuation should stay to ~240
        self.assertAlmostEqual(self.product1.total_value, 240, delta=0.04)
        self.assertAlmostEqual(self.product1.qty_available, 19)

        self.assertEqual(self.product1.standard_price, 12.63)

    def test_fifo_sublocation_valuation_1(self):
        """ Set the main stock as a view location. Receive 2 units of a
        product, put 1 unit in an internal sublocation and the second
        one in a scrap sublocation. Only a single unit, the one in the
        internal sublocation, should be valued. Then, send these two
        quants to a customer, only the one in the internal location
        should be valued.
        """
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.standard_price = 10

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
        })

        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.write({'move_line_ids': [
            (5, 0, 0),
            (0, None, {
                'product_id': self.product1.id,
                'quantity': 1,
                'location_id': self.supplier_location.id,
                'location_dest_id': subloc1.id,
                'product_uom_id': self.uom_unit.id
            }),
            (0, None, {
                'product_id': self.product1.id,
                'quantity': 1,
                'location_id': self.supplier_location.id,
                'location_dest_id': subloc2.id,
                'product_uom_id': self.uom_unit.id
            }),
        ]})
        move1.picked = True
        move1._action_done()
        self.assertEqual(move1.value, 10)
        self.assertEqual(move1.remaining_qty, 1)
        self.assertAlmostEqual(self.product1._with_valuation_context().qty_available, 1.0)
        self.assertEqual(self.product1.total_value, 10)

        move2 = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2.0,
        })
        move2._action_confirm()
        move2._action_assign()

        move2.write({'move_line_ids': [
            (5, 0, 0),
            (0, None, {
                'product_id': self.product1.id,
                'quantity': 1,
                'location_id': subloc1.id,
                'location_dest_id': self.supplier_location.id,
                'product_uom_id': self.uom_unit.id
            }),
            (0, None, {
                'product_id': self.product1.id,
                'quantity': 1,
                'location_id': subloc2.id,
                'location_dest_id': self.supplier_location.id,
                'product_uom_id': self.uom_unit.id
            }),
        ]})
        move2.picked = True
        move2._action_done()
        self.assertEqual(move2.value, 10)
        self.assertEqual(move1.remaining_qty, 0)
        self.assertAlmostEqual(self.product1.qty_available, 0.0)
        self.assertEqual(self.product1.total_value, 0)

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
        })

        move1 = self.env['stock.move'].create({
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
                'quantity': 1,
                'location_id': self.stock_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_id': self.uom_unit.id
            }),
            (0, None, {
                'product_id': self.product1.id,
                'quantity': 1,
                'location_id': self.stock_location.id,
                'location_dest_id': scrap.id,
                'product_uom_id': self.uom_unit.id
            }),
        ]})
        move1.picked = True
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
                'quantity': 1,
                'location_id': customer1.id,
                'location_dest_id': self.stock_location.id,
                'product_uom_id': self.uom_unit.id
            }),
            (0, None, {
                'product_id': self.product1.id,
                'quantity': 1,
                'location_id': self.stock_location.id,
                'location_dest_id': customer1.id,
                'product_uom_id': self.uom_unit.id
            }),
        ]})
        move2.picked = True
        self.assertEqual(move2._is_in(), True)
        self.assertEqual(move2._is_out(), True)

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
        with freeze_time(date1):
            self.product1.standard_price = 10.0

        # receive 10
        with freeze_time(date2):
            self._make_in_move(self.product1, 10)

        self.assertEqual(self.product1.qty_available, 10)
        self.assertEqual(self.product1.total_value, 100)

        # receive 20
        with freeze_time(date3):
            self._make_in_move(self.product1, 20)

        self.assertEqual(self.product1.qty_available, 30)
        self.assertEqual(self.product1.total_value, 300)

        # send 15
        with freeze_time(date4):
            self._make_out_move(self.product1, 15)

        self.assertEqual(self.product1.qty_available, 15)
        self.assertEqual(self.product1.total_value, 150)

        # set the standard price to 5
        with freeze_time(date5):
            self.product1.standard_price = 5

        self.assertEqual(self.product1.qty_available, 15)
        self.assertEqual(self.product1.total_value, 75)

        # send 10
        with freeze_time(date6):
            self._make_out_move(self.product1, 10)

        self.assertEqual(self.product1.qty_available, 5)
        self.assertEqual(self.product1.total_value, 25.0)

        # set the standard price to 7.5
        with freeze_time(date7):
            self.product1.standard_price = 7.5

        # receive 90
        with freeze_time(date8):
            self._make_in_move(self.product1, 90)

        self.assertEqual(self.product1.qty_available, 95)
        self.assertEqual(self.product1.total_value, 712.5)

        # Quantity available at date
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date1)).qty_available, 0)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date2)).qty_available, 10)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date3)).qty_available, 30)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date4)).qty_available, 15)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date5)).qty_available, 15)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date6)).qty_available, 5)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date7)).qty_available, 5)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date8)).qty_available, 95)

        # Valuation at date
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date1)).total_value, 0)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date2)).total_value, 100)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date3)).total_value, 300)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date4)).total_value, 150)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date5)).total_value, 75)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date6)).total_value, 25)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date8)).total_value, 712.5)

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
        with freeze_time(date1):
            move1 = self._make_in_move(self.product1, 10, 10)

        self.assertEqual(self.product1.qty_available, 10)
        self.assertEqual(self.product1.total_value, 100)

        # receive 10@12
        with freeze_time(date2):
            self._make_in_move(self.product1, 10, 12)

        self.assertAlmostEqual(self.product1.qty_available, 20)
        self.assertEqual(self.product1.total_value, 220)

        # send 15
        with freeze_time(date3):
            self._make_out_move(self.product1, 15)

        self.assertAlmostEqual(self.product1.qty_available, 5.0)
        self.assertEqual(self.product1.total_value, 60)

        # send 20
        with freeze_time(date4):
            self._make_out_move(self.product1, 20)

        self.assertAlmostEqual(self.product1.qty_available, -15.0)
        self.assertEqual(self.product1.total_value, -180)

        # receive 100@15
        with freeze_time(date5):
            self._make_in_move(self.product1, 100, 15)

        self.assertEqual(self.product1.qty_available, 85)
        self.assertEqual(self.product1.total_value, 1275)

        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date1)).qty_available, 10)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date1)).total_value, 100)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date2)).qty_available, 20)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date2)).total_value, 220)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date3)).qty_available, 5)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date3)).total_value, 60)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date4)).qty_available, -15)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date4)).total_value, -180)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date5)).qty_available, 85)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date5)).total_value, 1275)

        # Edit the quantity done of move1, increase it.
        # Test a limitation, you can keep the old value but you can't keep the quantity in past
        with freeze_time(date6):
            self._set_quantity(move1, 20)
        self.assertEqual(self.product1.qty_available, 95)
        self.assertEqual(self.product1.total_value, 1425)

        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date1)).qty_available, 20)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date1)).total_value, 100)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date2)).qty_available, 30)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date2)).total_value, 220)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date3)).qty_available, 15)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date3)).total_value, 145)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date4)).qty_available, -5)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date4)).total_value, -60)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date5)).qty_available, 95)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date5)).total_value, 1425)

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
            'location_id': inventory_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 12.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 12.0
        move1.picked = True
        move1._action_done()
        move1.value_manual = 180.0

        self.assertAlmostEqual(move1.value, 180.0)
        self.assertAlmostEqual(move1.remaining_qty, 12.0)
        self.assertAlmostEqual(self.product1.total_value, 180.0)
        self.product1._invalidate_cache()

        # Sell the 12 units
        move2 = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 12.0,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 12.0
        move2.picked = True
        move2._action_done()

        move1._invalidate_cache()
        self.assertAlmostEqual(move1.remaining_qty, 0.0)
        self.assertAlmostEqual(self.product1.total_value, 0.0)

    def test_at_date_average_1(self):
        """ Set a company on the inventory loss, take items from there then put items there, check
        the values and quantities at date.
        """
        now = Datetime.now()
        date1 = now - timedelta(days=8)
        date2 = now - timedelta(days=7)

        self.product1.standard_price = 10
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        inventory_location = self.product1.property_stock_inventory
        inventory_location.company_id = self.env.company.id

        move1 = self.env['stock.move'].create({
            'location_id': inventory_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 10.0
        move1.picked = True
        move1._action_done()
        move1.date = date1

        move2 = self.env['stock.move'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': inventory_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 5.0
        move2.picked = True
        move2._action_done()
        move2.date = date2

        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date1)).qty_available, 10)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date1)).total_value, 100)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date2)).qty_available, 5)
        self.assertEqual(self.product1.with_context(to_date=Datetime.to_string(date2)).total_value, 50)

    def test_forecast_report_value(self):
        """ Create a SVL for two companies using different currency, and open
        the forecast report. Checks the forecast report use the good currency to
        display the product's valuation.
        """
        # Settings
        self.product1.categ_id.property_valuation = 'periodic'
        # Creates two new currencies.
        currency_1 = self.env['res.currency'].create({
            'name': 'UNF',
            'symbol': 'U',
            'rounding': 0.01,
            'currency_unit_label': 'Unifranc',
            'rate': 1,
            'position': 'before',
        })
        currency_2 = self.env['res.currency'].create({
            'name': 'DBL',
            'symbol': 'DD',
            'rounding': 0.01,
            'currency_unit_label': 'Doublard',
            'rate': 2,
        })
        # Create a new company using the "Unifranc" as currency.
        company_form = Form(self.env['res.company'])
        company_form.name = "BB Inc."
        company_form.currency_id = currency_1
        company_1 = company_form.save()
        # Create a new company using the "Doublard" as currency.
        company_form = Form(self.env['res.company'])
        company_form.name = "BB Corp"
        company_form.currency_id = currency_2
        company_2 = company_form.save()
        # Gets warehouses and locations.
        warehouse_1 = self.env['stock.warehouse'].search([('company_id', '=', company_1.id)], limit=1)
        warehouse_2 = self.env['stock.warehouse'].search([('company_id', '=', company_2.id)], limit=1)
        stock_1 = warehouse_1.lot_stock_id
        stock_2 = warehouse_2.lot_stock_id
        self.env.user.company_ids += company_1
        self.env.user.company_ids += company_2
        # Updates the product's value.
        self.product1.with_company(company_1).standard_price = 10
        self.product1.with_company(company_2).standard_price = 12

        # ---------------------------------------------------------------------
        # Receive 5 units @ 10.00 per unit (company_1)
        # ---------------------------------------------------------------------
        move_1 = self.env['stock.move'].with_company(company_1).create({
            'location_id': self.supplier_location.id,
            'location_dest_id': stock_1.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5.0,
        })
        move_1._action_confirm()
        move_1.move_line_ids.quantity = 5.0
        move_1.picked = True
        move_1._action_done()

        # ---------------------------------------------------------------------
        # Receive 4 units @ 12.00 per unit (company_2)
        # ---------------------------------------------------------------------
        move_2 = self.env['stock.move'].with_company(company_2).create({
            'location_id': self.supplier_location.id,
            'location_dest_id': stock_2.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4.0,
        })
        move_2._action_confirm()
        move_2.move_line_ids.quantity = 4.0
        move_2.picked = True
        move_2._action_done()

        # Opens the report for each company and compares the values.
        report = self.env['stock.forecasted_product_product']
        report_for_company_1 = report.with_company(company_1).with_context(warehouse_id=warehouse_1.id)
        report_for_company_2 = report.with_company(company_2).with_context(warehouse_id=warehouse_2.id)
        report_value_1 = report_for_company_1.get_report_values(docids=self.product1.ids)
        report_value_2 = report_for_company_2.get_report_values(docids=self.product1.ids)
        self.assertEqual(report_value_1['docs']['value'], "U 50.00")
        self.assertEqual(report_value_2['docs']['value'], "48.00 DD")

    def test_fifo_and_sml_owned_by_company(self):
        """
        When receiving a FIFO product, if the picking is owned by the company,
        there should be a SVL and an account move linked to the product SM
        """
        self.product1.categ_id.property_cost_method = 'fifo'

        receipt = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
            'owner_id': self.env.company.partner_id.id,
            'state': 'draft',
        })

        move = self._make_in_move(self.product1, 1, 10, create_picking=True, owner=self.env.company.partner_id)

        closing_move = self.env['account.move'].browse(move.company_id.action_close_stock_valuation()['res_id'])
        self.assertEqual(move.value, 10)
        self.assertEqual(closing_move.amount_total, 10)

    def test_create_receipts_different_uom(self):
        """
        Create a transfer and use in the move a different unit of measure than
        the one set on the product form and ensure that when the qty done is changed
        and the picking is already validated, an svl is created in the uom set in the product.
        """
        uom_dozen = self.env.ref('uom.product_uom_dozen')
        receipt = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
            'owner_id': self.env.company.partner_id.id,
            'state': 'draft',
        })

        move = self.env['stock.move'].create({
            'picking_id': receipt.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': uom_dozen.id,
            'product_uom_qty': 1.0,
            'price_unit': 10,
        })
        receipt.action_confirm()
        move.quantity = 1
        move.picked = True
        receipt.button_validate()

        self.assertEqual(self.product1.uom_name, 'Units')
        self.assertEqual(self.product1.qty_available, 12)
        move.quantity = 2
        self.assertEqual(self.product1.qty_available, 24)

    def test_average_manual_price_change(self):
        """
        When doing a Manual Price Change, an SVL is created to update the total_value.
        This test check that the value of this SVL is correct and does result in new_std_price * quantity.
        To do so, we create 2 In moves, which result in a standard price rounded at $5.29, the non-rounded value ≃ 5.2857.
        Then we update the standard price to $7
        """
        self.product1.categ_id.property_cost_method = 'average'
        self._make_in_move(self.product1, 5, unit_cost=5)
        self._make_in_move(self.product1, 2, unit_cost=6)

        # make sure field 'value' is flagged as aggregatable
        self.assertEqual(
            self.env['stock.quant'].fields_get(['value'], ['aggregator']),
            {'value': {'aggregator': 'sum'}},
            "Field 'value' must be aggregatable.",
        )

        res = self.env['stock.quant']._read_group([('product_id', '=', self.product1.id)], aggregates=['value:sum'])
        self.assertEqual(res[0][0], 5 * 5 + 2 * 6)
        # Avoid inderterminism since product.value and stock.move could have the same datetime in _run_avco
        with freeze_time(Datetime.now() + timedelta(minutes=1)):
            self.product1.standard_price = 7
        self.assertEqual(self.product1.total_value, 49)

    def test_average_manual_revaluation(self):
        self.product1.categ_id.property_cost_method = 'average'

        move1 = self._make_in_move(self.product1, 1, unit_cost=20)
        move1.value_manual = 20
        move2 = self._make_in_move(self.product1, 1, unit_cost=30)
        move2.value_manual = 30
        self.assertEqual(self.product1.standard_price, 25)

        move2.value_manual = 20
        self.assertEqual(self.product1.standard_price, 20)

    def test_fifo_manual_revaluation(self):
        revaluation_vals = {
            'default_product_id': self.product1.id,
            'default_company_id': self.env.company.id,
            'default_account_id': self.stock_valuation_account,
        }
        self.product1.categ_id.property_cost_method = 'fifo'

        move1 = self._make_in_move(self.product1, 1, unit_cost=15)
        move1.value_manual = 15
        move2 = self._make_in_move(self.product1, 1, unit_cost=30)
        move2.value_manual = 30
        self.assertEqual(self.product1.standard_price, 22.5)

        move2.value_manual = 20
        self.assertEqual(self.product1.standard_price, 17.5)

    def test_manual_revaluation_statement(self):
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

        move1 = self._make_in_move(self.product1, 1, unit_cost=15)
        move1.value_manual = 15
        move1.value_manual = 25
        self.assertEqual(self.product1.standard_price, 25.0)

    def test_journal_entries_from_change_product_cost_method(self):
        """ Changing between non-standard cost methods when an underlying product has real_time
        accounting and a negative on hand quantity should result in journal entries with offsetting
        debit/credits for the stock valuation and stock output accounts (inverse of positive qty).
        """
        self.product1.categ_id.property_cost_method = 'fifo'
        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom_qty': 10.0,
            'price_unit': 7.2,
        })
        move2 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom_qty': 20.0,
            'price_unit': 15.3,
        })
        (move1 + move2)._action_confirm()
        (move1 + move2)._action_assign()
        move1.quantity = 10
        move2.quantity = 20
        (move1 + move2).picked = True
        (move1 + move2)._action_done()
        move1.value_manual = 72.0
        move2.value_manual = 306.0
        move3 = self.env['stock.move'].create({
            'product_id': self.product1.id,
            'product_uom_qty': 100,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        move3._action_confirm()
        move3._action_assign()
        move3.quantity = 100
        move3.picked = True
        move3._action_done()
        self.product1.categ_id.property_cost_method = 'average'

        closing_move = self.env['account.move'].browse(move3.company_id.action_close_stock_valuation()['res_id'])
        valuation_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.stock_valuation_account)
        expense_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.expense_account)

        self.assertRecordValues(
            valuation_aml + expense_aml,
            [
                {'account_id': self.stock_valuation_account.id, 'debit': 0.0, 'credit': 882.0},
                {'account_id': self.expense_account.id, 'debit': 882.0, 'credit': 0.0},
            ]
        )

    def test_journal_entries_from_change_category(self):
        """ Changing category having a different cost methods when an underlying product has real_time
        accounting and a negative on hand quantity should result in journal entries with offsetting
        debit/credits for the stock valuation and stock output accounts (inverse of positive qty).
        """
        self.product1.categ_id.property_cost_method = 'fifo'
        other_categ = self.product1.categ_id.copy({
            'property_cost_method': 'average',
            'property_stock_valuation_account_id': self.stock_valuation_account.id,
            'property_stock_journal': self.stock_journal.id,
        })
        move1 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom_qty': 10.0,
            'price_unit': 7.2,
        })
        move2 = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom_qty': 20.0,
            'price_unit': 15.3,
        })
        (move1 + move2)._action_confirm()
        (move1 + move2)._action_assign()
        move1.quantity = 10
        move2.quantity = 20
        (move1 + move2).picked = True
        (move1 + move2)._action_done()
        move1.value_manual = 72.0
        move2.value_manual = 306.0
        move3 = self.env['stock.move'].create({
            'product_id': self.product1.id,
            'product_uom_qty': 100,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        move3._action_confirm()
        move3._action_assign()
        move3.quantity = 100
        move3.picked = True
        move3._action_done()
        self.product1.product_tmpl_id.categ_id = other_categ

        closing_move = self.env['account.move'].browse(move3.company_id.action_close_stock_valuation()['res_id'])
        valuation_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.stock_valuation_account)
        expense_aml = closing_move.line_ids.filtered(lambda l: l.account_id == self.expense_account)

        self.assertRecordValues(
            valuation_aml + expense_aml,
            [
                {'account_id': self.stock_valuation_account.id, 'debit': 0.0, 'credit': 882.0},
                {'account_id': self.expense_account.id, 'debit': 882.0, 'credit': 0.0},
            ]
        )

    def test_diff_uom_quantity_update_after_done(self):
        """Test that when the UoM of the stock.move.line is different from the stock.move,
        the quantity update after done (unlocked) use the correct UoM"""
        unit_uom = self.env.ref('uom.product_uom_unit')
        dozen_uom = self.env.ref('uom.product_uom_dozen')
        move = self.env['stock.move'].create({
            'product_id': self.product1.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.stock_location.id,
            'product_uom': unit_uom.id,
            'product_uom_qty': 12,
            'price_unit': 1,
            'picking_type_id': self.picking_type_in.id,
        })
        move._action_confirm()
        move._action_assign()

        # Change from 12 Units to 1 Dozen (aka: same quantity)
        move.move_line_ids = [
            Command.update(
                move.move_line_ids[0].id,
                {'quantity': 1, 'product_uom_id': dozen_uom.id}
            )
        ]
        move.picked = True
        move._action_done()

        self.assertEqual(move.quantity, 12)

        move.picking_id.action_toggle_is_locked()
        # Change from 1 Dozen to 2 Dozens (12 -> 24)
        move.move_line_ids = [Command.update(move.move_line_ids[0].id, {'quantity': 2})]

        self.assertEqual(move.quantity, 24)

    def test_internal_location_with_no_company(self):
        """ An internal location without a company should not be valued """
        location = self.env['stock.location'].create({
            'name': 'Internal no company',
            'usage': 'internal',
            'company_id': False,
        })
        self.assertFalse(location._should_be_valued())

        move = self.env['stock.move'].create({
            'product_id': self.product1.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': location.id,
            'product_uom_qty': 1,
            'price_unit': 1,
        })
        move._action_confirm()
        move._action_assign()
        move.quantity = 1
        move.picked = True
        move._action_done()

        self.assertEqual(move.state, "done")
        self.assertEqual(self.product1.qty_available, 0)

    def test_stock_valuation_layer_revaluation_with_branch_company(self):
        """
        Test that the product price is updated in the branch company
        by taking into account only the stock valuation layer of the branch company.
        """
        self.assertEqual(self.product1.standard_price, 0)
        self.product1.categ_id.property_cost_method = 'average'
        move1 = self._make_in_move(self.product1, 1, unit_cost=20)
        move1.value_manual = 20
        self.assertEqual(self.product1.standard_price, 20)
        # create a branch company
        branch = self.env['res.company'].create({
            'name': "Branch A",
            'parent_id': self.env.company.id,
        })
        # Create a move in the branch company
        self.patch(self, 'env', branch.with_company(branch).env)
        self.product1.with_company(branch).categ_id.property_cost_method = 'average'
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', branch.id)], limit=1)
        move2 = self._make_in_move(self.product1, 1, unit_cost=30, location_dest_id=warehouse.lot_stock_id.id, picking_type_id=warehouse.in_type_id.id)
        move2.value_manual = 30
        self.assertEqual(self.product1.with_company(branch).standard_price, 30)

    def test_action_done_with_state_already_done(self):
        """ This test ensure that calling _action_done on a move already done
        has no effect on the valuation.
        """
        self.product1.standard_price = 10

        in_move = self.env['stock.move'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom_qty': 10.0,
            'picked': True,
            'quantity': 10,
        })
        # Call _action_done twice, only 1 layer should be created
        in_move._action_done()
        self.assertEqual(in_move.state, 'done')
        in_move._action_done()

        self.assertEqual(in_move.value, 100)
        self.assertEqual(in_move.quantity, 10)

    def test_scrap_reception_valuation(self):
        product = self.product1
        product.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'periodic'
        receipt = self._make_in_move(self.product1, 10, 15, create_picking=True).picking_id
        scrap_location = self.env['stock.location'].search(
            [('name', '=', 'Scrap'), ('company_id', '=', self.env.company.id)], limit=1
        )
        scrap_location.valuation_account_id = self.inventory_adjustment_account
        scrap_form = Form(self.env['stock.scrap'].with_context(default_picking_id=receipt.id))
        scrap_form.product_id = product
        scrap_form.scrap_qty = 2
        scrap = scrap_form.save()
        scrap.action_validate()
        self.assertRecordValues(
            receipt.move_ids,
            [
                {'quantity': 10.0, 'remaining_qty': 8.0, 'value': 150.0, 'remaining_value': 120.0},
                {'quantity': 2.0, 'remaining_qty': 0.0, 'value': 30.0, 'remaining_value': 0.0},
            ]
        )

    def test_positive_stock_adjustment_valuation(self):
        accounts_data = self.product1.product_tmpl_id.get_product_accounts()
        inventory_adjustment_loc = self.env['stock.location'].search(
            [('usage', '=', 'inventory'), ('company_id', '=', self.env.company.id)], limit=1
        )
        inventory_adjustment_loc.valuation_account_id = self.stock_valuation_account
        self.product1.standard_price = 10
        inventory_gain_move = self._make_in_move(self.product1, 10, location_id=inventory_adjustment_loc.id)

        amls = inventory_gain_move.account_move_id.line_ids
        self.assertEqual(len(amls), 2)
        debit_line = amls.filtered(lambda l: l.debit > 0)
        credit_line = amls.filtered(lambda l: l.credit > 0)
        self.assertEqual(debit_line.account_id, accounts_data['stock_valuation'])
        self.assertEqual(credit_line.account_id, accounts_data['stock_valuation'])

    def test_negative_stock_adjustment_valuation(self):
        accounts_data = self.product1.product_tmpl_id.get_product_accounts()
        inventory_adjustment_loc = self.env['stock.location'].search(
            [('usage', '=', 'inventory'), ('company_id', '=', self.env.company.id)], limit=1
        )
        inventory_adjustment_loc.valuation_account_id = self.stock_valuation_account
        self.product1.standard_price = 10
        self._make_in_move(self.product1, 10)
        inventory_loss_move = self._make_out_move(self.product1, 5, location_dest_id=inventory_adjustment_loc.id)

        amls = inventory_loss_move.account_move_id.line_ids
        self.assertEqual(len(amls), 2)
        debit_line = amls.filtered(lambda l: l.debit > 0)
        credit_line = amls.filtered(lambda l: l.credit > 0)
        self.assertEqual(debit_line.account_id, accounts_data['stock_valuation'])
        self.assertEqual(credit_line.account_id, accounts_data['stock_valuation'])

    def test_valuation_rounding_method(self):
        uom_g = self.env.ref('uom.product_uom_gram')
        uom_kg = self.env.ref('uom.product_uom_kgm')
        self.product1.uom_id = uom_kg

        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'move_ids': [Command.create({
                'product_id': self.product1.id,
                'product_uom': uom_g.id,
                'product_uom_qty': 11,
                'quantity': 11,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
            })],
        })
        receipt.button_validate()

        self.assertEqual(receipt.move_ids.quantity, 11)
        self.assertEqual(receipt.move_ids.product_qty, 0.01)
        self.assertEqual(self.product1.qty_available, 0.01)

        move_out = self._make_out_move(self.product1, 11, uom_id=uom_g.id)

        self.assertEqual(move_out.quantity, 11)
        self.assertEqual(move_out.product_qty, 0.01)
        self.assertEqual(self.product1.qty_available, 0.00)
