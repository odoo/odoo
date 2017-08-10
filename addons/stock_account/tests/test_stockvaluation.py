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

    def test_fifo_perpetual_1(self):
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
        move1.action_confirm()
        move1.action_assign()
        move1.move_line_ids.qty_done = 68.0
        move1.action_done()

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

        self.assertEqual(move3.price_unit, 0.0)  # unused in out moves

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
        move8.action_confirm()
        move8.action_assign()
        move8.move_line_ids.qty_done = 10.0
        move8.action_done()

        self.assertEqual(move8.value, 0.0)
        self.assertEqual(move8.cumulated_value, 0.0)

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
        move9.action_confirm()
        move9.action_assign()
        move9.move_line_ids.qty_done = 10.0
        move9.action_done()

        # note: it' ll have to get 10 units from move5 so its value should
        # be -(10*16.50) = -165
        self.assertEqual(move9.value, -165.0)
        self.assertEqual(move9.cumulated_value, 726.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 0)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move4.remaining_qty, 0.0)
        self.assertEqual(move5.remaining_qty, 44.0)
        self.assertEqual(move6.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move7.remaining_qty, 0.0)  # unused in out moves
        self.assertEqual(move8.remaining_qty, 0.0)  # unused in internal moves
        self.assertEqual(move9.remaining_qty, 0.0)  # unused in out moves

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

        self.assertEqual(move3.price_unit, 0.0)  # unused in out moves

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
        self.assertEqual(move1.remaining_qty, 0.0)  # unusedin average move

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

        # Sale 190 units @ 15.35 per unit
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

        self.assertEqual(move3.price_unit, 0.0)  # unused in out moves

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
        move5.with_context(debug=True).action_done()

        self.assertEqual(move5.value, -477.6)
        self.assertEqual(move5.cumulated_value, 795.9)  # fuck you, rounding
        # self.assertEqual(move5.cumulated_value, 796)

    def test_fifo_negative_1(self):
        self.product1.product_tmpl_id.cost_method = 'fifo'
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
        move1.action_confirm()
        move1.action_done()

        self.assertEqual(move1.value, 0.0)
        self.assertEqual(move1.cumulated_value, 0.0)
        # normally unused in out moves, but as it moved negative stock we mark it
        self.assertEqual(move1.remaining_qty, 50.0)

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
        move2.action_confirm()
        move2.action_done()

        self.assertEqual(move1.value, -600.0)
        self.assertEqual(move1.cumulated_value, -600.0)
        self.assertEqual(move1.remaining_qty, 10.0)
        self.assertEqual(move2.value, 600.0)
        self.assertEqual(move2.remaining_qty, 0.0)
        self.assertEqual(move2.cumulated_value, 0.0)

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
        move3.action_confirm()
        move3.action_done()

        self.assertEqual(move1.value, -850.0)
        self.assertEqual(move1.cumulated_value, -850.0)
        self.assertEqual(move1.remaining_qty, 0.0)
        self.assertEqual(move2.value, 600.0)
        self.assertEqual(move2.remaining_qty, 0.0)
        self.assertEqual(move2.cumulated_value, -250.0)
        self.assertEqual(move3.value, 500.0)
        self.assertEqual(move3.remaining_qty, 10.0)
        self.assertEqual(move3.cumulated_value, 250.0)

    def test_average_negative_1(self):
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
        move1.action_confirm()
        move1.force_assign()
        move1.quantity_done = 10.0
        move1.action_done()
        self.assertEqual(move1.value, -990.0)  # as no move out were done for this product, fallback on the standard price
        self.assertEqual(move1.cumulated_value, -990.0)
        self.assertEqual(move1.remaining_qty, 0.0)  # unused in average move

    def test_average_negative_2(self):
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
        move1.action_confirm()
        move1.action_assign()
        move1.move_line_ids.qty_done = 10.0
        move1.action_done()

        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.cumulated_value, 100.0)
        self.assertEqual(move1.remaining_qty, 0.0)  # unused in average move

        # send 10 products
        move2 = self.env['stock.move'].create({
            'name': 'Sale 94 units @ 19.00 per unit',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move2.action_confirm()
        move2.action_assign()
        move2.move_line_ids.qty_done = 10.0
        move2.action_done()

        self.assertEqual(move2.value, -100.0)
        self.assertEqual(move2.cumulated_value, 0.0)
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
        move3.action_confirm()
        move3.force_assign()
        move3.quantity_done = 10.0
        move3.action_done()

        self.assertEqual(move3.value, -100.0)  # as no move out were done for this product, fallback on latest cost
        self.assertEqual(move3.cumulated_value, -100.0)
        self.assertEqual(move3.remaining_qty, 0.0)  # unused in average move
