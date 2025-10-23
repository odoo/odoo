""" Implementation of "INVENTORY VALUATION TESTS" spreadsheet. """

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.stock_account.tests.common import TestStockValuationCommon
from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged


class TestStockValuationStandard(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.product_standard

    def test_normal_1(self):
        self._make_in_move(self.product, 10)
        self._make_in_move(self.product, 10)
        self._make_out_move(self.product, 15)

        self.assertEqual(self.product.total_value, 50)
        self.assertEqual(self.product.qty_available, 5)

    def test_change_in_past_increase_in_1(self):
        move1 = self._make_in_move(self.product, 10)
        self._make_in_move(self.product, 10)
        self._make_out_move(self.product, 15)
        move1.move_line_ids.quantity = 15

        self.assertEqual(self.product.total_value, 100)
        self.assertEqual(self.product.qty_available, 10)

    def test_change_in_past_decrease_in_1(self):
        move1 = self._make_in_move(self.product, 10)
        self._make_in_move(self.product, 10)
        self._make_out_move(self.product, 15)
        move1.move_line_ids.quantity = 5

        self.assertEqual(self.product.total_value, 0)
        self.assertEqual(self.product.qty_available, 0)

    def test_change_in_past_add_ml_in_1(self):
        move1 = self._make_in_move(self.product, 10)
        self._make_in_move(self.product, 10)
        self._make_out_move(self.product, 15)
        self.env['stock.move.line'].create({
            'move_id': move1.id,
            'product_id': move1.product_id.id,
            'quantity': 5,
            'product_uom_id': move1.product_uom.id,
            'location_id': move1.location_id.id,
            'location_dest_id': move1.location_dest_id.id,
        })

        self.assertEqual(self.product.total_value, 100)
        self.assertEqual(self.product.qty_available, 10)

    def test_change_in_past_increase_out_1(self):
        self._make_in_move(self.product, 10)
        move2 = self._make_out_move(self.product, 1)
        move2.move_line_ids.quantity = 5

        self.assertEqual(self.product.total_value, 50)
        self.assertEqual(self.product.qty_available, 5)

    def test_change_in_past_decrease_out_1(self):
        self._make_in_move(self.product, 10)
        move2 = self._make_out_move(self.product, 5)
        move2.move_line_ids.quantity = 1

        self.assertEqual(self.product.total_value, 90)
        self.assertEqual(self.product.qty_available, 9)

    def test_change_standard_price_1(self):
        self._make_out_move(self.product, 15)
        self._make_in_move(self.product, 10)
        self._make_in_move(self.product, 10)

        # change cost from 10 to 15
        self.product.standard_price = 15.0

        self.assertEqual(self.product.total_value, 75)
        self.assertEqual(self.product.qty_available, 5)
        self.assertEqual(self.product.avg_cost, 15)

    def test_negative_1(self):
        move1 = self._make_in_move(self.product, 10)
        self._make_out_move(self.product, 15)
        self.env['stock.move.line'].create({
            'move_id': move1.id,
            'product_id': move1.product_id.id,
            'quantity': 10,
            'product_uom_id': move1.product_uom.id,
            'location_id': move1.location_id.id,
            'location_dest_id': move1.location_dest_id.id,
        })

        self.assertEqual(self.product.total_value, 50)
        self.assertEqual(self.product.qty_available, 5)

    def test_dropship_1(self):
        self._make_dropship_move(self.product, 10)

        self.assertEqual(self.product.total_value, 0)
        self.assertEqual(self.product.qty_available, 0)

    def test_change_in_past_increase_dropship_1(self):
        move1 = self._make_dropship_move(self.product, 10)
        move1.move_line_ids.quantity = 15

        self.assertEqual(self.product.total_value, 0)
        self.assertEqual(self.product.qty_available, 0)

    def test_empty_stock_move_valuation(self):
        product1 = self.env['product.product'].create({
            'name': 'p1',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_expenses').id,
        })
        product2 = self.env['product.product'].create({
            'name': 'p2',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_expenses').id,
        })
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
        })
        for product in (product1, product2):
            product.standard_price = 10
            in_move = self.env['stock.move'].create({
                'product_id': product.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_uom': self.uom.id,
                'product_uom_qty': 2,
                'price_unit': 10,
                'picking_type_id': self.picking_type_in.id,
                'picking_id': picking.id
            })

        picking.action_confirm()
        # set quantity done only on one move
        in_move.move_line_ids.quantity = 2
        in_move.picked = True
        res_dict = picking.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].with_context(res_dict.get('context')).browse(res_dict.get('res_id'))
        wizard.process()

        self.assertEqual(product1.total_value, 0)
        self.assertEqual(product2.total_value, 20)

    def test_currency_precision_and_standard_value(self):
        currency = self.env['res.currency'].create({
            'name': 'Odoo',
            'symbol': 'O',
            'rounding': 1,
        })
        new_company = self.env['res.company'].create({
            'name': 'Super Company',
            'currency_id': currency.id,
        })

        old_company = self.env.user.company_id
        try:
            self.env.user.company_id = new_company
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', new_company.id)])
            product = self.product.with_company(new_company)
            product.standard_price = 3

            self._make_in_move(product, 0.5, location_dest_id=warehouse.lot_stock_id.id, picking_type_id=warehouse.in_type_id.id)
            self._make_out_move(product, 0.5, location_id=warehouse.lot_stock_id.id, picking_type_id=warehouse.out_type_id.id)

            self.assertEqual(product.total_value, 0.0)
        finally:
            self.env.user.company_id = old_company

    def test_change_qty_and_locations_of_done_sml(self):
        sub_stock_loc = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })

        move_in = self._make_in_move(self.product, 25)
        self.assertEqual(self.product.total_value, 250)
        self.assertEqual(self.product.qty_available, 25)

        move_in.move_line_ids.write({
            'location_dest_id': sub_stock_loc.id,
            'quantity': 30,
        })
        self.assertEqual(self.product.total_value, 300)
        self.assertEqual(self.product.qty_available, 30)

        sub_loc_quant = self.product.stock_quant_ids.filtered(lambda q: q.location_id == sub_stock_loc)
        self.assertEqual(sub_loc_quant.quantity, 30)


class TestStockValuationAVCO(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.product_avco

    def test_normal_1(self):
        self._make_in_move(self.product, 10, unit_cost=10)
        self.assertEqual(self.product.standard_price, 10)
        self._make_in_move(self.product, 10, unit_cost=20)
        self.assertEqual(self.product.standard_price, 15)
        self._make_out_move(self.product, 15)
        self.assertEqual(self.product.standard_price, 15)

        self.assertEqual(self.product.total_value, 75)
        self.assertEqual(self.product.qty_available, 5)

    def test_change_in_past_increase_in_1(self):
        move1 = self._make_in_move(self.product, 10, unit_cost=10)
        self._make_in_move(self.product, 10, unit_cost=20)
        self._make_out_move(self.product, 15)
        self._set_quantity(move1, 15)

        self.assertEqual(self.product.total_value, 140)
        self.assertEqual(self.product.qty_available, 10)
        self.assertEqual(self.product.standard_price, 14)

    def test_change_in_past_decrease_in_1(self):
        move1 = self._make_in_move(self.product, 10, unit_cost=10)
        self._make_in_move(self.product, 10, unit_cost=20)
        self._make_out_move(self.product, 15)
        self._set_quantity(move1, 5)

        self.assertEqual(self.product.total_value, 0)
        self.assertEqual(self.product.qty_available, 0)

    def test_change_in_past_add_ml_in_1(self):
        move1 = self._make_in_move(self.product, 10, unit_cost=10)
        self._make_in_move(self.product, 10, unit_cost=20)
        self._make_out_move(self.product, 15)
        self._add_move_line(move1, quantity=5)

        self.assertEqual(self.product.total_value, 140)
        self.assertEqual(self.product.qty_available, 10)
        self.assertEqual(self.product.standard_price, 14)

    def test_change_in_past_add_move_in_1(self):
        move1 = self._make_in_move(self.product, 10, unit_cost=10, create_picking=True)
        self._make_in_move(self.product, 10, unit_cost=20)
        self._make_out_move(self.product, 15)
        self._add_move_line(move1, quantity=5, state='done', picking_id=move1.picking_id.id)

        self.assertEqual(self.product.total_value, 140)
        self.assertEqual(self.product.qty_available, 10)
        self.assertEqual(self.product.standard_price, 14)

    def test_change_in_past_increase_out_1(self):
        self._make_in_move(self.product, 10, unit_cost=10)
        self._make_in_move(self.product, 10, unit_cost=20)
        move3 = self._make_out_move(self.product, 15)
        self._set_quantity(move3, 20)

        self.assertEqual(self.product.total_value, 0)
        self.assertEqual(self.product.qty_available, 0)
        self.assertEqual(self.product.standard_price, 15)

    def test_change_in_past_decrease_out_1(self):
        self._make_in_move(self.product, 10, unit_cost=10)
        self._make_in_move(self.product, 10, unit_cost=20)
        move3 = self._make_out_move(self.product, 15)
        self._set_quantity(move3, 10)

        self.assertEqual(self.product.total_value, 150)
        self.assertEqual(self.product.qty_available, 10)
        self.assertEqual(self.product.standard_price, 15)

    def test_negative_1(self):
        self._make_in_move(self.product, 10, unit_cost=10)
        self._make_in_move(self.product, 10, unit_cost=20)
        self._make_out_move(self.product, 30)
        self._make_in_move(self.product, 10, unit_cost=30)
        self._make_in_move(self.product, 10, unit_cost=40)

        self.assertEqual(self.product.total_value, 400)
        self.assertEqual(self.product.qty_available, 10)

    def test_negative_2(self):
        self.product.standard_price = 10
        self._make_out_move(self.product, 1, force_assign=True)
        self._make_in_move(self.product, 1, unit_cost=15)

        self.assertEqual(self.product.total_value, 0)
        self.assertEqual(self.product.qty_available, 0)

    def test_return_receipt_1(self):
        move1 = self._make_in_move(self.product, 1, unit_cost=10, create_picking=True)
        self._make_in_move(self.product, 1, unit_cost=20)
        self._make_out_move(self.product, 1)
        self._make_return(move1, 1)

        self.assertEqual(self.product.total_value, 0)
        self.assertEqual(self.product.qty_available, 0)
        self.assertEqual(self.product.standard_price, 15)

    def test_return_delivery_1(self):
        self._make_in_move(self.product, 1, unit_cost=10)
        self._make_in_move(self.product, 1, unit_cost=20)
        move3 = self._make_out_move(self.product, 1, create_picking=True)
        self._make_return(move3, 1)

        self.assertEqual(self.product.total_value, 30)
        self.assertEqual(self.product.qty_available, 2)
        self.assertEqual(self.product.standard_price, 15)

    def test_rereturn_receipt_1(self):
        move1 = self._make_in_move(self.product, 1, unit_cost=10, create_picking=True)
        self._make_in_move(self.product, 1, unit_cost=20)
        self._make_out_move(self.product, 1)
        move4 = self._make_return(move1, 1)  # -15, current avco
        self._make_return(move4, 1)  # +10, original move's price unit

        self.assertEqual(self.product.total_value, 15)
        self.assertEqual(self.product.qty_available, 1)
        self.assertEqual(self.product.standard_price, 15)

    def test_rereturn_delivery_1(self):
        self._make_in_move(self.product, 1, unit_cost=10)
        self._make_in_move(self.product, 1, unit_cost=20)
        move3 = self._make_out_move(self.product, 1, create_picking=True)
        move4 = self._make_return(move3, 1)
        self._make_return(move4, 1)

        self.assertEqual(self.product.total_value, 15)
        self.assertEqual(self.product.qty_available, 1)
        self.assertEqual(self.product.standard_price, 15)

    def test_dropship_1(self):
        self._make_in_move(self.product, 1, unit_cost=10)
        self._make_in_move(self.product, 1, unit_cost=20)
        self._make_dropship_move(self.product, 1, unit_cost=10)

        self.assertEqual(self.product.total_value, 30)
        self.assertEqual(self.product.qty_available, 2)
        self.assertEqual(self.product.standard_price, 15)

    def test_rounding_1(self):
        self._make_in_move(self.product, 1, unit_cost=1.00)
        self._make_in_move(self.product, 1, unit_cost=1.00)
        self._make_in_move(self.product, 1, unit_cost=1.01)

        self.assertAlmostEqual(self.product.total_value, 3.01)

        self._make_out_move(self.product, 3, create_picking=True)

        self.assertEqual(self.product.total_value, 0)
        self.assertEqual(self.product.qty_available, 0)
        self.assertEqual(self.product.standard_price, 1.00)

    def test_rounding_2(self):
        self._make_in_move(self.product, 1, unit_cost=1.02)
        self._make_in_move(self.product, 1, unit_cost=1.00)
        self._make_in_move(self.product, 1, unit_cost=1.00)

        self.assertAlmostEqual(self.product.total_value, 3.02)

        self._make_out_move(self.product, 3, create_picking=True)

        self.assertEqual(self.product.total_value, 0)
        self.assertEqual(self.product.qty_available, 0)
        self.assertEqual(self.product.standard_price, 1.01)

    def test_rounding_3(self):
        self._make_in_move(self.product, 1000, unit_cost=0.17)
        self._make_in_move(self.product, 800, unit_cost=0.23)

        self.assertEqual(self.product.standard_price, 0.20)

        self._make_out_move(self.product, 1000, create_picking=True)
        self._make_out_move(self.product, 800, create_picking=True)

        self.assertEqual(self.product.total_value, 0)

    def test_rounding_4(self):
        """
        The first 2 In moves result in a rounded standard_price at 3.4943, which is rounded at 3.49.
        This test ensures that no rounding error is generated with small out quantities.
        """
        self._make_in_move(self.product, 2, unit_cost=4.63)
        self._make_in_move(self.product, 5, unit_cost=3.04)
        self.assertEqual(self.product.standard_price, 3.49)

        for _ in range(70):
            self._make_out_move(self.product, 0.1)

        self.assertEqual(self.product.qty_available, 0)
        self.assertEqual(self.product.total_value, 0)

    def test_rounding_5(self):
        self._make_in_move(self.product, 10, unit_cost=16.83)
        self._make_in_move(self.product, 10, unit_cost=20)
        self.assertEqual(self.product.standard_price, 18.42)

        self._make_out_move(self.product, 10)
        out_move = self._make_out_move(self.product, 9)
        self.assertEqual(out_move.value, 165.78)

        self.assertEqual(self.product.total_value, 18.42)
        self.assertEqual(self.product.qty_available, 1)

        self._make_out_move(self.product, 1)
        self.assertEqual(self.product.total_value, 0)
        self.assertEqual(self.product.qty_available, 0)

    def test_return_delivery_2(self):
        self.product.standard_price = 1
        move1 = self._make_out_move(self.product, 10, create_picking=True, force_assign=True)
        self._make_in_move(self.product, 10, unit_cost=2)
        self._make_return(move1, 10)

        self.assertEqual(self.product.total_value, 10)
        self.assertEqual(self.product.qty_available, 10)
        self.assertEqual(self.product.standard_price, 1)

    def test_return_delivery_rounding(self):
        self._make_in_move(self.product, 1, unit_cost=13.13)
        self._make_in_move(self.product, 1, unit_cost=12.20)
        move3 = self._make_out_move(self.product, 2, create_picking=True)
        move4 = self._make_return(move3, 2)

        self.assertAlmostEqual(abs(move3.value), abs(move4.value))
        self.assertAlmostEqual(self.product.total_value, 25.34)
        self.assertEqual(self.product.qty_available, 2)


class TestStockValuationFIFO(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.product_fifo

    def test_normal_1(self):
        self._make_in_move(self.product, 10, unit_cost=10)
        self._make_in_move(self.product, 10, unit_cost=20)
        self._make_out_move(self.product, 15)

        self.assertEqual(self.product.total_value, 100)
        self.assertEqual(self.product.qty_available, 5)

    def test_negative_1(self):
        self._make_in_move(self.product, 10, unit_cost=10)
        self._make_in_move(self.product, 10, unit_cost=20)
        self._make_out_move(self.product, 30)
        self.assertEqual(self.product.qty_available, -10)
        self._make_in_move(self.product, 10, unit_cost=30)
        self.assertEqual(self.product.qty_available, 0)
        self._make_in_move(self.product, 10, unit_cost=40)

        self.assertEqual(self.product.total_value, 400)
        self.assertEqual(self.product.qty_available, 10)

    def test_change_in_past_decrease_in_1(self):
        move1 = self._make_in_move(self.product, 20, unit_cost=10)
        self._make_out_move(self.product, 10)
        self._set_quantity(move1, 10)

        self.assertEqual(self.product.total_value, 0)
        self.assertEqual(self.product.qty_available, 0)

    def test_change_in_past_decrease_in_2(self):
        move1 = self._make_in_move(self.product, 20, unit_cost=10)
        self._make_out_move(self.product, 10)
        self._make_out_move(self.product, 10)
        self._set_quantity(move1, 10)
        self._make_in_move(self.product, 20, unit_cost=15)

        self.assertEqual(self.product.total_value, 150)
        self.assertEqual(self.product.qty_available, 10)

    def test_change_in_past_increase_in_1(self):
        move1 = self._make_in_move(self.product, 10, unit_cost=10)
        self._make_in_move(self.product, 10, unit_cost=15)
        self._make_out_move(self.product, 20)
        self._set_quantity(move1, 20)

        self.assertEqual(self.product.total_value, 150)
        self.assertEqual(self.product.qty_available, 10)

    def test_change_in_past_increase_in_2(self):
        move1 = self._make_in_move(self.product, 10, unit_cost=10)
        self._make_in_move(self.product, 10, unit_cost=12)
        self._make_out_move(self.product, 15)
        self._make_out_move(self.product, 20)
        self._make_in_move(self.product, 100, unit_cost=15)
        self._set_quantity(move1, 20)

        self.assertEqual(self.product.total_value, 1425)
        self.assertEqual(self.product.qty_available, 95)

    def test_change_in_past_increase_out_1(self):
        self._make_in_move(self.product, 20, unit_cost=10)
        move2 = self._make_out_move(self.product, 10)
        self._make_in_move(self.product, 20, unit_cost=15)
        self._set_quantity(move2, 25)

        self.assertEqual(self.product.total_value, 225)
        self.assertEqual(self.product.qty_available, 15)

    def test_change_in_past_decrease_out_1(self):
        """ Decrease the quantity of an outgoing stock.move.line will act like
        an inventory adjustement and not a return. It will take the move value
        in order to set the value and not the standard price of the product.
        """
        self._make_in_move(self.product, 20, unit_cost=10)
        move2 = self._make_out_move(self.product, 15)
        self._make_in_move(self.product, 20, unit_cost=15)
        self._set_quantity(move2, 5)

        self.assertEqual(self.product.total_value, 450)
        self.assertEqual(self.product.qty_available, 35)

    def test_change_in_past_add_ml_out_1(self):
        self._make_in_move(self.product, 20, unit_cost=10)
        move2 = self._make_out_move(self.product, 10)
        self._make_in_move(self.product, 20, unit_cost=15)
        self._add_move_line(move2, quantity=5)

        self.assertEqual(self.product.total_value, 350)
        self.assertEqual(self.product.qty_available, 25)

    def test_return_delivery_1(self):
        self._make_in_move(self.product, 10, unit_cost=10)
        move2 = self._make_out_move(self.product, 10, create_picking=True)
        self._make_in_move(self.product, 10, unit_cost=20)
        self._make_return(move2, 10)

        self.assertEqual(self.product.total_value, 300)
        self.assertEqual(self.product.qty_available, 20)

    def test_return_receipt_1(self):
        move1 = self._make_in_move(self.product, 10, unit_cost=10, create_picking=True)
        self._make_in_move(self.product, 10, unit_cost=20)
        self._make_return(move1, 2)

        self.assertEqual(self.product.total_value, 280)
        self.assertEqual(self.product.qty_available, 18)

    def test_rereturn_receipt_1(self):
        move1 = self._make_in_move(self.product, 1, unit_cost=10, create_picking=True)
        self._make_in_move(self.product, 1, unit_cost=20)
        self._make_out_move(self.product, 1)
        move4 = self._make_return(move1, 1)
        self._make_return(move4, 1)

        self.assertEqual(self.product.total_value, 20)
        self.assertEqual(self.product.qty_available, 1)

    def test_rereturn_delivery_1(self):
        self._make_in_move(self.product, 1, unit_cost=10)
        self._make_in_move(self.product, 1, unit_cost=20)
        move3 = self._make_out_move(self.product, 1, create_picking=True)
        move4 = self._make_return(move3, 1)
        self._make_return(move4, 1)

        self.assertEqual(self.product.total_value, 10)
        self.assertEqual(self.product.qty_available, 1)

    def test_dropship_1(self):
        self._make_in_move(self.product, 1, unit_cost=10)
        self._make_in_move(self.product, 1, unit_cost=20)
        self._make_dropship_move(self.product, 1, unit_cost=10)

        self.assertEqual(self.product.total_value, 30)
        self.assertEqual(self.product.qty_available, 2)
        self.assertAlmostEqual(self.product.standard_price, 15)

    def test_return_delivery_2(self):
        self._make_in_move(self.product, 1, unit_cost=10)
        self.product.standard_price = 0
        self._make_in_move(self.product, 1, unit_cost=0)

        self._make_out_move(self.product, 1)
        out_move02 = self._make_out_move(self.product, 1, create_picking=True)

        returned = self._make_return(out_move02, 1)
        self.assertEqual(returned.value, 0)

    def test_return_delivery_3(self):
        self.product.standard_price = 1
        move1 = self._make_out_move(self.product, 10, create_picking=True, force_assign=True)
        self._make_in_move(self.product, 10, unit_cost=2)
        self._make_return(move1, 10)

        self.assertEqual(self.product.total_value, 10)
        self.assertEqual(self.product.qty_available, 10)

    def test_currency_precision_and_fifo_value(self):
        currency = self.env['res.currency'].create({
            'name': 'Odoo',
            'symbol': 'O',
            'rounding': 1,
        })
        new_company = self.env['res.company'].create({
            'name': 'Super Company',
            'currency_id': currency.id,
        })

        old_company = self.env.user.company_id
        try:
            self.env.user.company_id = new_company
            product = self.product.with_company(new_company)
            product.product_tmpl_id.categ_id.property_cost_method = 'fifo'
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', new_company.id)])

            self._make_in_move(product, 0.5, location_dest_id=warehouse.lot_stock_id.id, picking_type_id=warehouse.in_type_id.id, unit_cost=3)
            self._make_out_move(product, 0.5, location_id=warehouse.lot_stock_id.id, picking_type_id=warehouse.out_type_id.id)

            self.assertEqual(product.total_value, 0.0)
        finally:
            self.env.user.company_id = old_company


class TestStockValuationChangeCostMethod(TestStockValuationCommon):
    def test_standard_to_fifo_1(self):
        """ The accounting impact of this cost method change is neutral.
        """
        self.product = self.product_standard
        self.product.product_tmpl_id.standard_price = 10

        self._make_in_move(self.product, 10)
        self._make_in_move(self.product, 10)
        self._make_out_move(self.product, 1)

        self.product.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.assertEqual(self.product.total_value, 190)
        self.assertEqual(self.product.qty_available, 19)

    def test_standard_to_fifo_2(self):
        """ We want the same result as `test_standard_to_fifo_1` but by changing the category of
        `self.product` to another one, not changing the current one.
        """
        self.product = self.product_standard
        self.product.product_tmpl_id.standard_price = 10

        self._make_in_move(self.product, 10)
        self._make_in_move(self.product, 10)
        self._make_out_move(self.product, 1)

        cat2 = self.env['product.category'].create({'name': 'fifo', 'property_cost_method': 'fifo'})
        self.product.product_tmpl_id.categ_id = cat2
        self.assertEqual(self.product.total_value, 190)
        self.assertEqual(self.product.qty_available, 19)

    def test_avco_to_fifo(self):
        """ The accounting impact of this cost method change is neutral.
        """
        self.product = self.product_avco

        self._make_in_move(self.product, 10, unit_cost=10)
        self._make_in_move(self.product, 10, unit_cost=20)
        self._make_out_move(self.product, 1)

        self.product.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.assertEqual(self.product.total_value, 290)
        self.assertEqual(self.product.qty_available, 19)

    def test_fifo_to_standard(self):
        """ The accounting impact of this cost method change is not neutral as we will use the last
        fifo price as the new standard price.
        """
        self.product = self.product_fifo

        self._make_in_move(self.product, 10, unit_cost=10)
        self._make_in_move(self.product, 10, unit_cost=20)
        self._make_out_move(self.product, 1)

        self.product.product_tmpl_id.categ_id.property_cost_method = 'standard'
        # last std price = 15.26 (290/19). Due to rounding, 15.26 * 19 = 289.94
        self.assertEqual(self.product.total_value, 289.94)
        self.assertEqual(self.product.qty_available, 19)

    def test_fifo_to_avco(self):
        """ The accounting impact of this cost method change is not neutral as we will use the last
        fifo price as the new AVCO.
        """
        self.product = self.product_fifo

        self._make_in_move(self.product, 10, unit_cost=10)
        self._make_in_move(self.product, 10, unit_cost=20)
        self._make_out_move(self.product, 1)

        self.product.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.assertEqual(self.product.total_value, 285)
        self.assertEqual(self.product.qty_available, 19)

    def test_avco_to_standard(self):
        """ The accounting impact of this cost method change is neutral.
        """
        self.product = self.product_avco

        self._make_in_move(self.product, 10, unit_cost=10)
        self._make_in_move(self.product, 10, unit_cost=20)
        self._make_out_move(self.product, 1)

        self.product.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.assertEqual(self.product.total_value, 285)
        self.assertEqual(self.product.qty_available, 19)

    def test_standard_to_avco(self):
        """ The accounting impact of this cost method change is neutral.
        """
        self.product = self.product_standard
        self.product.product_tmpl_id.standard_price = 10

        self._make_in_move(self.product, 10)
        self._make_in_move(self.product, 10)
        self._make_out_move(self.product, 1)

        self.product.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.assertEqual(self.product.total_value, 190)
        self.assertEqual(self.product.qty_available, 19)


@tagged('post_install', '-at_install', 'change_valuation')
class TestStockValuationChangeValuation(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super(TestStockValuationChangeValuation, cls).setUpClass()
        cls.product = cls.product_standard

    def test_standard_manual_to_auto_1(self):
        self.product.product_tmpl_id.standard_price = 10
        self._make_in_move(self.product, 10)

        self.assertEqual(self.product.total_value, 100)
        self.assertEqual(self.product.qty_available, 10)

        self.product.product_tmpl_id.categ_id.write({
            'property_valuation': 'real_time',
            'property_stock_valuation_account_id': self.account_stock_valuation.id,
        })

        self.assertEqual(self.product.total_value, 100)
        self.assertEqual(self.product.qty_available, 10)

        account_move_line = self.env['account.move'].browse(self.env.company.action_close_stock_valuation()['res_id']).line_ids
        self.assertEqual(len(account_move_line), 2)

    def test_standard_manual_to_auto_2(self):
        self.product.product_tmpl_id.standard_price = 10
        self._make_in_move(self.product, 10)

        self.assertEqual(self.product.total_value, 100)
        self.assertEqual(self.product.qty_available, 10)

        # Try to change the product category with a `default_type` key in the context and
        # check it doesn't break the account move generation.
        self.product.with_context(default_is_storable=True).categ_id = self.category_standard_auto
        self.assertEqual(self.product.categ_id, self.category_standard_auto)

        self.assertEqual(self.product.total_value, 100)
        self.assertEqual(self.product.qty_available, 10)

        account_move_line = self.env['account.move'].browse(self.env.company.action_close_stock_valuation()['res_id']).line_ids
        self.assertEqual(len(account_move_line), 2)

    def test_standard_auto_to_manual_1(self):
        self.product = self.product_standard_auto
        self.product.product_tmpl_id.standard_price = 10
        self._make_in_move(self.product, 10)

        self.assertEqual(self.product.total_value, 100)
        self.assertEqual(self.product.qty_available, 10)

        self.product.product_tmpl_id.categ_id.property_valuation = 'periodic'

        self.assertEqual(self.product.total_value, 100)
        self.assertEqual(self.product.qty_available, 10)

        # An accounting entry should only be created for the emptying now that the category is manual.
        account_move_line = self.env['account.move'].browse(self.env.company.action_close_stock_valuation()['res_id']).line_ids
        self.assertEqual(len(account_move_line), 2)

    def test_standard_auto_to_manual_2(self):
        self.product = self.product_standard_auto
        self.product.product_tmpl_id.standard_price = 10
        self._make_in_move(self.product, 10)

        self.assertEqual(self.product.total_value, 100)
        self.assertEqual(self.product.qty_available, 10)

        self.product.with_context(debug=True).categ_id = self.category_standard

        self.assertEqual(self.product.total_value, 100)
        self.assertEqual(self.product.qty_available, 10)

        # account_move_line = self.env['account.move'].browse(self.env.company.action_close_stock_valuation()['res_id']).line_ids
        # self.assertEqual(len(account_move_line), 2)

    def test_return_delivery_fifo(self):
        self.product = self.product_fifo
        self.env['decimal.precision'].search([
            ('name', '=', 'Product Price'),
        ]).digits = 4
        self.product.standard_price = 280.8475

        move1 = self._make_out_move(self.product, 4, create_picking=True, force_assign=True)
        move2 = self._make_return(move1, 4)

        for move in [move1, move2]:
            self.assertAlmostEqual(move._get_price_unit(), self.product.standard_price)
            self.assertAlmostEqual(abs(move.value), 1123.39)


class TestAngloSaxonAccounting(TestStockValuationCommon):
    def test_avco_and_credit_note(self):
        """
        When reversing an invoice that contains some anglo-saxo AML, the new anglo-saxo AML should have the same value
        """
        # Required for `account_id` to be visible in the view
        self.env.user.group_ids += self.env.ref('account.group_account_readonly')
        self.product = self.product_avco_auto

        self._make_in_move(self.product, 2, unit_cost=10)

        invoice = self._create_invoice(self.product, 2, 25)

        self._make_in_move(self.product, 2, unit_cost=20)
        # self.assertEqual(self.product.standard_price, 15)

        refund_wizard = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice.ids).create({
            'journal_id': invoice.journal_id.id,
        })
        action = refund_wizard.refund_moves()
        reverse_invoice = self.env['account.move'].browse(action['res_id'])
        with Form(reverse_invoice) as reverse_invoice_form:
            with reverse_invoice_form.invoice_line_ids.edit(0) as line:
                line.quantity = 1
        reverse_invoice.action_post()

        anglo_lines = reverse_invoice.line_ids.filtered(lambda l: l.display_type == 'cogs')
        self.assertEqual(len(anglo_lines), 2)
        self.assertEqual(abs(anglo_lines[0].balance), 10)
        self.assertEqual(abs(anglo_lines[1].balance), 10)

    def test_return_delivery_storno(self):
        """ When using STORNO accounting, reverse accounting moves should have negative values for credit/debit.
        """
        self.env.company.account_storno = True
        self.product = self.product_fifo

        self._make_in_move(self.product, 10, unit_cost=10)
        out_move = self._make_out_move(self.product, 10, create_picking=True)
        self._make_return(out_move, 10)

        out_invoice = self._create_invoice(self.product, 10, 10)
        return_credit_note = self._create_credit_note(self.product, 10, 10, reversed_entry_id=out_invoice.id)

        out_move_line_ids = out_invoice.line_ids

        self.assertEqual(out_move_line_ids[0].credit, 100)
        self.assertEqual(out_move_line_ids[0].debit, 0)
        self.assertEqual(out_move_line_ids[1].credit, 0)
        self.assertEqual(out_move_line_ids[1].debit, 100)

        return_line_ids = return_credit_note.line_ids

        self.assertEqual(return_line_ids[0].credit, -100)
        self.assertEqual(return_line_ids[0].debit, 0)
        self.assertEqual(return_line_ids[1].credit, 0)
        self.assertEqual(return_line_ids[1].debit, -100)
