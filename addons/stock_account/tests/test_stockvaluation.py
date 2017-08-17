# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestStockValuation(TransactionCase):
    def setUp(self):
        super(TestStockValuation, self).setUp()
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.uom_unit = self.env.ref('product.product_uom_unit')
        self.product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })

    def test_fifo_negative_1(self):
        self.product1.product_tmpl_id.cost_method = 'fifo'
        # Beginning Inventory: 68 units @ 15.00 per unit
        move1 = self.env['stock.move'].create({
            'name': '50 out',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 50.0,
            'price_unit': 0,
            'move_line_ids': [(0, 0, {'product_id': self.product1.id,
                                      'location_id': self.stock_location.id,
                                      'location_dest_id': self.customer_location.id,
                                      'product_uom_id': self.uom_unit.id,
                                      'qty_done': 50.0})]
        })
        move1.action_confirm()
        move1.action_done()
        
        move2 = self.env['stock.move'].create({
            'name': '40 in @15',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 40.0,
            'price_unit': 15.0,
            'move_line_ids': [(0, 0, {'product_id': self.product1.id,
                                      'location_id': self.supplier_location.id,
                                      'location_dest_id': self.stock_location.id,
                                      'product_uom_id': self.uom_unit.id,
                                      'qty_done': 40.0})]
        })
        move2.action_confirm()
        move2.action_done()
        move3 = self.env['stock.move'].create({
            'name': '20 in @25',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 20.0,
            'price_unit': 25.0,
            'move_line_ids': [(0, 0, {'product_id': self.product1.id,
                                      'location_id': self.supplier_location.id,
                                      'location_dest_id': self.stock_location.id,
                                      'product_uom_id': self.uom_unit.id,
                                      'qty_done': 20.0})]
        })
        move3.action_confirm()
        move3.action_done()
        
        self.assertEqual(self.product1.stock_value, 250.0, 'Stock value should be 250')
        self.assertEqual(move1.value, -850.0, 'Stock value should be -850')
        self.assertEqual(move2.value, 600.0, 'Stock value should be 600')
        self.assertEqual(move3.value, 500.0, 'Stock value should be 500')


    def test_fifo_perpetual_1(self):
        # http://accountingexplained.com/financial/inventories/fifo-method
        self.product1.product_tmpl_id.cost_method = 'fifo'
        self.product1.product_tmpl_id.valuation = 'real_time'
        Account = self.env['account.account']
        # Maybe the localization has not been installed yet
        stock_input_account = Account.create({'name': 'Stock Input', 
                                              'code': 'StockIn',
                                              'user_type_id': self.env.ref('account.data_account_type_current_assets').id,})
        stock_output_account = Account.create({'name': 'Stock Output', 
                                              'code': 'StockOut',
                                              'user_type_id': self.env.ref('account.data_account_type_current_assets').id,})
        stock_valuation_account = Account.create({'name': 'Stock Valuation', 
                                              'code': 'Stock Valuation',
                                              'user_type_id': self.env.ref('account.data_account_type_current_assets').id,})
        stock_journal = self.env['account.journal'].create({'name': 'Stock Journal', 
                                            'code': 'STJTEST',
                                            'type': 'general'})
        self.product1.categ_id.write({'property_stock_account_input_categ_id': stock_input_account.id,
                                      'property_stock_account_output_categ_id': stock_output_account.id,
                                      'property_stock_valuation_account_id': stock_valuation_account.id,
                                      'property_stock_journal': stock_journal.id,
                                      })
        
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
        move1.action_confirm()
        move1.action_assign()
        move1.move_line_ids.qty_done = 68.0
        move1.action_done()
        
        # Check accounting entries
        Aml = self.env['account.move.line']
        self.assertEqual(Aml.search([('product_id', '=', self.product1.id), ('debit', '>', 0)]).account_id.id, stock_valuation_account.id, 'Problem valuation account entry')
        self.assertEqual(Aml.search([('product_id', '=', self.product1.id), ('credit', '>', 0)]).account_id.id, stock_input_account.id, 'Problem input account entry')

        self.assertEqual(move1.value, 1020.0)
        self.assertEqual(move1.cumulated_value, 1020.0)

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
        move2.action_confirm()
        move2.action_assign()
        move2.move_line_ids.qty_done = 140.0
        move2.action_done()

        self.assertEqual(move2.value, 2170.0)
        self.assertEqual(move2.cumulated_value, 3190.0)

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
        move3.action_confirm()
        move3.action_assign()
        move3.move_line_ids.qty_done = 94.0
        move3.action_done()
        self.assertEqual(Aml.search([('product_id', '=', self.product1.id), ('debit', '>', 0), 
                                           ('account_id', '!=', stock_valuation_account.id)]).account_id.id, stock_output_account.id, 'Output account entry problem')


        # note: it' ll have to get 68 units from the first batch and 26 from the second one
        # so its value should be -((68*15) + (26*15.5)) = -1423
        self.assertEqual(move3.value, -1423.0)
        self.assertEqual(move3.cumulated_value, 1767.0)

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
        move4.action_confirm()
        move4.action_assign()
        move4.move_line_ids.qty_done = 40.0
        move4.action_done()

        self.assertEqual(move4.value, 640.0)
        self.assertEqual(move4.cumulated_value, 2407.0)

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
        move5.action_confirm()
        move5.action_assign()
        move5.move_line_ids.qty_done = 78.0
        move5.action_done()

        self.assertEqual(move5.value, 1287.0)
        self.assertEqual(move5.cumulated_value, 3694.0)

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
        move6.action_confirm()
        move6.action_assign()
        move6.move_line_ids.qty_done = 116.0
        move6.action_done()

        # note: it' ll have to get 114 units from the move2 and 2 from move4
        # so its value should be -((114*15.5) + (2*16)) = 1735
        self.assertEqual(move6.value, -1799.0)
        self.assertEqual(move6.cumulated_value, 1895.0)

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
        move7.action_confirm()
        move7.action_assign()
        move7.move_line_ids.qty_done = 62.0
        move7.action_done()

        # note: it' ll have to get 38 units from the move4 and 24 from move5
        # so its value should be -((38*16) + (24*16.5)) = 608 + 396
        self.assertEqual(move7.value, -1004.0)
        self.assertEqual(move7.cumulated_value, 891.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 0)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.remaining_qty, 0.0)
        self.assertEqual(move5.remaining_qty, 54.0)
        self.assertEqual(move6.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move7.remaining_qty, 0.0)  # unused in out moves
        # Test what happens when we change the stock in the past
        amls = Aml.search([('account_id', '=', stock_valuation_account.id), ('product_id', '=', self.product1.id)])
        self.assertEqual(sum(x.debit and x.debit or -x.credit for x in amls), 891.0, 'Valuation Entries should sum to the stock value of 891')

        move3.quantity_done = 10
        self.assertEqual(move1.value, 1020.0)
        self.assertEqual(move2.value, 2170.0)
        self.assertEqual(move3.value, -150.0)
        self.assertEqual(move4.value, 640.0)
        self.assertEqual(move5.value, 1287.0)
        self.assertEqual(move6.value, -1769.0)
        self.assertEqual(move7.value, -961.0)
        self.assertEqual(move7.cumulated_value, 2237.0)
        self.assertEqual(move7.last_done_qty, 138.0)
        move6.move_line_ids.qty_done = 120.0
        amls = Aml.search([('account_id', '=', stock_output_account.id), ('product_id', '=', self.product1.id), ('credit', '>', 0)])
        self.assertEqual(sum(x.credit for x in amls), 1346.0, 'Decreasing the quantity on an out is like a return and should credit the stock output account')

    def test_fifo_perpetual_2(self):
        # https://docs.google.com/spreadsheets/d/1NI0u9N1gFByXxYHfdiXuxQCrycXXOh76TpPQ3CWeyDw/edit?ts=58da749b#gid=0
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
        move1.action_confirm()
        move1.action_assign()
        move1.move_line_ids.qty_done = 10.0
        move1.action_done()

        self.assertEqual(move1.value, 1000.0)
        self.assertEqual(move1.cumulated_value, 1000.0)
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
        move2.action_confirm()
        move2.action_assign()
        move2.move_line_ids.qty_done = 10.0
        move2.action_done()

        self.assertEqual(move2.value, 800.0)
        self.assertEqual(move2.cumulated_value, 1800.0)

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
        move3.action_confirm()
        move3.action_assign()
        move3.move_line_ids.qty_done = 15.0
        move3.action_done()


        # note: it' ll have to get 10 units from move1 and 5 from move2
        # so its value should be -((10*100) + (5*80)) = -1423
        self.assertEqual(move3.value, -1400.0)
        self.assertEqual(move3.cumulated_value, 400.0)

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
        move4.action_confirm()
        move4.action_assign()
        move4.move_line_ids.qty_done = 5.0
        move4.action_done()

        self.assertEqual(move4.value, 300.0)
        self.assertEqual(move4.cumulated_value, 700.0)

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
        move5.action_confirm()
        move5.action_assign()
        move5.move_line_ids.qty_done = 7.0
        move5.action_done()

        # note: it' ll have to get 5 units from the move2 and 2 from move4
        # so its value should be -((5*80) + (2*60)) = 520
        self.assertEqual(move5.value, -520.0)
        self.assertEqual(move5.cumulated_value, 180.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 0)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.remaining_qty, 3.0)
        self.assertEqual(move5.remaining_qty, 0.0)  # unused in out moves

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
        move1.action_confirm()
        move1.action_assign()
        move1.move_line_ids.qty_done = 60.0
        move1.action_done()

        self.assertEqual(move1.value, 900.0)
        self.assertEqual(move1.cumulated_value, 900.0)

        self.assertEqual(move1.remaining_qty, 60.0)

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
        move2.action_confirm()
        move2.action_assign()
        move2.move_line_ids.qty_done = 140.0
        move2.action_done()

        self.assertEqual(move2.value, 2170.0)
        self.assertEqual(move2.cumulated_value, 3070.0)

        # Sale 190 units @ 15.00 per unit
        move3 = self.env['stock.move'].create({
            'name': 'Sale 190 units @ 19.00 per unit',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 190.0,
        })
        move3.action_confirm()
        move3.action_assign()
        move3.move_line_ids.qty_done = 190.0
        move3.action_done()


        self.assertEqual(move3.value, -2916.5)
        self.assertEqual(move3.cumulated_value, 153.5)

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
        move4.action_confirm()
        move4.action_assign()
        move4.move_line_ids.qty_done = 70.0
        move4.action_done()

        self.assertEqual(move4.value, 1120.0)
        self.assertEqual(move4.cumulated_value, 1273.5)

        # Sale 30 units @ $19.50 per unit
        move5 = self.env['stock.move'].create({
            'name': '30 units @ $19.50 per unit',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 30.0,
        })
        move5.action_confirm()
        move5.action_assign()
        move5.move_line_ids.qty_done = 30.0
        move5.action_done()

        self.assertEqual(move5.value, -477.6)
        self.assertEqual(move5.cumulated_value, 795.9)  # fuck you, rounding
        
        move3.move_line_ids.qty_done = 90.0
        self.assertEqual(round(move5.cumulated_value, 1), 2340.4)
        
        
        # Test changing from average to fifo cost method
        self.product1.product_tmpl_id.cost_method = 'fifo'
        self.assertEqual(move4.value, 1092.0, 'The value of the move 4')
        self.assertEqual(move4.remaining_qty, 70.0, 'Remaining qty should be set')
        
        self.assertEqual(move2.value, 2178.0, 'The value of the move 2 should be a mix of existing price and the original price on the move')
        self.assertEqual(move2.remaining_qty, 80.0, 'The remaining qty should be set to 80.0.')
        self.assertEqual(move1.remaining_qty, 0.0, 'The remaining qty is 0.0')