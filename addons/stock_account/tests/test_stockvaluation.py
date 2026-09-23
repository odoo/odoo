from datetime import timedelta

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import UserError
from odoo.fields import Date, Datetime
from odoo.tests import Form

from odoo.addons.stock_account.tests.common import TestStockValuationCommon


class TestStockValuation(TestStockValuationCommon):
    def test_realtime(self):
        product = self.product_standard_auto
        product.standard_price = 5.0
        move1 = self._make_in_move(product, 10, 5)

        closing_move = self._close()
        debit_line = closing_move.line_ids.filtered(lambda l: l.debit > 0)
        self.assertEqual(len(debit_line), 1)
        self.assertEqual(debit_line.debit, 50.0)
        self.assertEqual(debit_line.credit, 0)
        product._invalidate_cache()

        product.standard_price = 6.0
        closing_move = self._close()
        debit_line = closing_move.line_ids.filtered(lambda l: l.debit > 0)
        self.assertEqual(len(debit_line), 1)
        self.assertEqual(debit_line.debit, 10.0)
        self.assertEqual(debit_line.credit, 0)
        self.assertEqual(move1.product_id, product)

    def test_realtime_consumable(self):
        product = self.product_standard_auto
        product.standard_price = 5.0
        product.is_storable = False
        self._make_in_move(product, 10, 5)
        with self.assertRaises(UserError):
            self._close()

    def test_fifo_perpetual_1(self):
        product = self.product_fifo

        move1 = self._make_in_move(product, 10, 10)

        self.assertEqual(move1._get_price_unit(), 10.0)
        self.assertEqual(move1.remaining_qty, 10.0)
        self.assertEqual(move1.value, 100.0)

        move2 = self._make_in_move(product, 10, 8)

        self.assertEqual(move2.remaining_qty, 10.0)
        self.assertEqual(move2.value, 80.0)

        move3 = self._make_out_move(product, 3)

        self.assertEqual(move3.value, 30.0)

        self._set_quantity(move1, 12)

        self.assertEqual(move1._get_price_unit(), 10.0)
        self.assertEqual(move1.remaining_qty, 9.0)
        self.assertEqual(move1.value, 120.0)

        move4 = self._make_out_move(product, 9)

        self.assertEqual(move4.value, 90.0)

        move5 = self._make_out_move(product, 20)

        self.assertEqual(move5.value, 160.0)
        closing_move = self._close()
        valuation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_valuation
        )
        variation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_variation
        )
        self.assertRecordValues(
            valuation_aml + variation_aml,
            [
                {
                    "account_id": self.account_stock_valuation.id,
                    "debit": 0,
                    "credit": 80,
                },
                {
                    "account_id": self.account_stock_variation.id,
                    "debit": 80,
                    "credit": 0,
                },
            ],
        )

        move6 = self._make_in_move(product, 10, 12)

        self.assertEqual(move6.value, 120.0)
        closing_move = self._close()
        valuation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_valuation
        )
        variation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_variation
        )
        self.assertRecordValues(
            valuation_aml + variation_aml,
            [
                {
                    "account_id": self.account_stock_valuation.id,
                    "debit": 80,
                    "credit": 0,
                },
                {
                    "account_id": self.account_stock_variation.id,
                    "debit": 0,
                    "credit": 80,
                },
            ],
        )
        self.assertEqual(
            sum(self._get_stock_valuation_move_lines().mapped("balance")), 0
        )

        self._set_quantity(move6, 8)
        self._close()
        self.assertEqual(
            sum(self._get_stock_valuation_move_lines().mapped("balance")), -24
        )

        self._make_in_move(product, 4, 15)
        self._close()
        self.assertEqual(product.total_value, 30)
        self.assertEqual(
            sum(self._get_stock_valuation_move_lines().mapped("balance")), 30
        )

    def test_fifo_perpetual_2(self):
        product = self.product_fifo

        move1 = self._make_in_move(product, 68, 15)

        self.assertEqual(move1.value, 1020.0)

        self.assertEqual(move1.remaining_qty, 68.0)

        move2 = self._make_in_move(product, 140, 15.5)

        self.assertEqual(move2.value, 2170.0)

        self.assertEqual(move1.remaining_qty, 68.0)
        self.assertEqual(move2.remaining_qty, 140.0)

        move3 = self._make_out_move(product, 94)

        self.assertEqual(move3.value, 1423.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 114)
        self.assertEqual(move3.remaining_qty, 0.0)

        move4 = self._make_in_move(product, 40, 16)

        self.assertEqual(move4.value, 640.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 114)
        self.assertEqual(move3.remaining_qty, 0.0)
        self.assertEqual(move4.remaining_qty, 40.0)

        move5 = self._make_in_move(product, 78, 16.5)

        self.assertEqual(move5.value, 1287.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 114)
        self.assertEqual(move3.remaining_qty, 0.0)
        self.assertEqual(move4.remaining_qty, 40.0)
        self.assertEqual(move5.remaining_qty, 78.0)

        move6 = self._make_out_move(product, 116)

        self.assertEqual(move6.value, 1799.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 0)
        self.assertEqual(move3.remaining_qty, 0.0)
        self.assertEqual(move4.remaining_qty, 38.0)
        self.assertEqual(move5.remaining_qty, 78.0)
        self.assertEqual(move6.remaining_qty, 0.0)

        move7 = self._make_out_move(product, 62)

        self.assertEqual(move7.value, 1004.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 0)
        self.assertEqual(move3.remaining_qty, 0.0)
        self.assertEqual(move4.remaining_qty, 0.0)
        self.assertEqual(move5.remaining_qty, 54.0)
        self.assertEqual(move6.remaining_qty, 0.0)
        self.assertEqual(move7.remaining_qty, 0.0)

        transit_location = self.env["stock.location"].search(
            [
                ("company_id", "=", self.company.id),
                ("usage", "=", "transit"),
                ("active", "=", False),
            ],
            limit=1,
        )
        transit_location.active = True
        move8 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": transit_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 10.0,
            }
        )
        move8._action_confirm()
        move8._action_assign()
        move8.move_line_ids.quantity = 10.0
        move8.picked = True
        move8._action_done()

        self.assertEqual(move8.value, 0.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 0)
        self.assertEqual(move3.remaining_qty, 0.0)
        self.assertEqual(move4.remaining_qty, 0.0)
        self.assertEqual(move5.remaining_qty, 54.0)
        self.assertEqual(move6.remaining_qty, 0.0)
        self.assertEqual(move7.remaining_qty, 0.0)
        self.assertEqual(move8.remaining_qty, 0.0)

        move9 = self._make_out_move(product, 10)

        self.assertEqual(move9.value, 165.0)

        self.assertEqual(move1.remaining_qty, 0)
        self.assertEqual(move2.remaining_qty, 0)
        self.assertEqual(move3.remaining_qty, 0.0)
        self.assertEqual(move4.remaining_qty, 0.0)
        self.assertEqual(move5.remaining_qty, 44.0)
        self.assertEqual(move6.remaining_qty, 0.0)
        self.assertEqual(move7.remaining_qty, 0.0)
        self.assertEqual(move8.remaining_qty, 0.0)
        self.assertEqual(move9.remaining_qty, 0.0)

    def test_fifo_perpetual_3(self):
        product = self.product_fifo

        move1 = self._make_in_move(product, 1.9, 10)

        self.assertAlmostEqual(move1.remaining_qty, 1.9)
        self.assertAlmostEqual(move1.remaining_value, 19)

    def test_fifo_negative_1(self):
        product = self.product_fifo

        with freeze_time(Datetime.now() - timedelta(seconds=1)):
            product.product_tmpl_id.standard_price = 8.0

        move1 = self._make_out_move(product, 50)

        self.assertEqual(move1.value, 400.0)
        self.assertEqual(move1.remaining_qty, 0.0)

        closing_move = self._close()
        valuation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_valuation
        )
        variation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_variation
        )
        self.assertRecordValues(
            valuation_aml + variation_aml,
            [
                {
                    "account_id": self.account_stock_valuation.id,
                    "debit": 0,
                    "credit": 400,
                },
                {
                    "account_id": self.account_stock_variation.id,
                    "debit": 400,
                    "credit": 0,
                },
            ],
        )

        move2 = self._make_in_move(product, 40, 15)

        self.assertEqual(move2.value, 600.0)
        self.assertEqual(move2.remaining_qty, 0)

        closing_move = self._close()
        valuation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_valuation
        )
        variation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_variation
        )
        self.assertRecordValues(
            valuation_aml + variation_aml,
            [
                {
                    "account_id": self.account_stock_valuation.id,
                    "debit": 250,
                    "credit": 0,
                },
                {
                    "account_id": self.account_stock_variation.id,
                    "debit": 0,
                    "credit": 250,
                },
            ],
        )

        self._make_in_move(product, 20, 25)

        closing_move = self._close()
        valuation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_valuation
        )
        variation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_variation
        )
        self.assertRecordValues(
            valuation_aml + variation_aml,
            [
                {
                    "account_id": self.account_stock_valuation.id,
                    "debit": 400,
                    "credit": 0,
                },
                {
                    "account_id": self.account_stock_variation.id,
                    "debit": 0,
                    "credit": 400,
                },
            ],
        )

        self.assertEqual(product.qty_available, 10)
        self.assertEqual(product.total_value, 250)
        self.assertEqual(
            sum(self._get_stock_valuation_move_lines().mapped("balance")), 250
        )
        self.assertEqual(
            sum(self._get_stock_variation_move_lines().mapped("balance")), -250
        )
        self.assertEqual(sum(self._get_expense_move_lines().mapped("balance")), 0)

    def test_fifo_negative_2(self):
        product = self.product_fifo

        move1 = self._make_in_move(product, 10, 10)

        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_qty, 10.0)

        move2 = self._make_out_move(product, 10, 10)

        self.assertEqual(move2.value, 100.0)
        self.assertEqual(move1.remaining_qty, 0.0)

        with self.assertRaises(UserError):
            self._close()

        move3 = self._make_out_move(product, 21)

        self.assertEqual(move3.value, 210.0)

        closing_move = self._close()
        valuation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_valuation
        )
        variation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_variation
        )
        self.assertRecordValues(
            valuation_aml + variation_aml,
            [
                {
                    "account_id": self.account_stock_valuation.id,
                    "debit": 0,
                    "credit": 210,
                },
                {
                    "account_id": self.account_stock_variation.id,
                    "debit": 210,
                    "credit": 0,
                },
            ],
        )

        self.assertEqual(product.qty_available, -21)
        self.assertEqual(product.total_value, -210)
        self.assertEqual(
            sum(self._get_stock_valuation_move_lines().mapped("balance")), -210
        )

    def test_fifo_add_move_in_done_picking_1(self):
        product = self.product_fifo
        product2 = self.product_fifo.copy()

        move1 = self._make_in_move(product, 10, 10, create_picking=True)
        receipt = move1.picking_id

        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_qty, 10.0)

        product2.standard_price = 20
        move2 = self.env["stock.move"].create(
            {
                "picking_id": receipt.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product2.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 10.0,
                "value_manual": 200.0,
                "move_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product2.id,
                            "location_id": self.supplier_location.id,
                            "location_dest_id": self.stock_location.id,
                            "product_uom_id": self.uom.id,
                            "quantity": 10.0,
                        },
                    )
                ],
            }
        )
        self.assertEqual(move2.state, "done")
        self.assertEqual(move2.value, 200.0)
        self.assertEqual(move2.remaining_qty, 10.0)
        self.assertEqual(product2.standard_price, 20.0)

        self.assertEqual(product.qty_available, 10)
        self.assertEqual(product.total_value, 100)
        self.assertEqual(product2.qty_available, 10)
        self.assertEqual(product2.total_value, 200)

        closing_move = self.env["account.move"].browse(
            move2.company_id.action_close_stock_valuation()["res_id"]
        )
        valuation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_valuation
        )
        variation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_variation
        )
        self.assertRecordValues(
            valuation_aml + variation_aml,
            [
                {
                    "account_id": self.account_stock_valuation.id,
                    "debit": 300,
                    "credit": 0,
                },
                {
                    "account_id": self.account_stock_variation.id,
                    "debit": 0,
                    "credit": 300,
                },
            ],
        )

        self._set_quantity(move2, 11)

        self.assertEqual(move2.value, 220.0)
        self.assertEqual(move2.quantity, 11.0)
        product2._invalidate_cache()
        product2.standard_price = 20.0

        closing_move = self.env["account.move"].browse(
            move2.company_id.action_close_stock_valuation()["res_id"]
        )
        valuation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_valuation
        )
        variation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_variation
        )
        self.assertRecordValues(
            valuation_aml + variation_aml,
            [
                {
                    "account_id": self.account_stock_valuation.id,
                    "debit": 320,
                    "credit": 0,
                },
                {
                    "account_id": self.account_stock_variation.id,
                    "debit": 0,
                    "credit": 320,
                },
            ],
        )

        move3 = self._make_out_move(product2, 11, create_picking=True)

        self.assertEqual(move3.value, 220.0)
        self.assertEqual(move3.remaining_qty, 0.0)
        self.assertEqual(product2.standard_price, 20.0)
        self.assertEqual(product2.qty_available, 0)
        product2._invalidate_cache()
        product2.standard_price = 20.0

        closing_move = self.env["account.move"].browse(
            move2.company_id.action_close_stock_valuation()["res_id"]
        )
        valuation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_valuation
        )
        variation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_variation
        )
        self.assertRecordValues(
            valuation_aml + variation_aml,
            [
                {
                    "account_id": self.account_stock_valuation.id,
                    "debit": 100,
                    "credit": 0,
                },
                {
                    "account_id": self.account_stock_variation.id,
                    "debit": 0,
                    "credit": 100,
                },
            ],
        )

    def test_fifo_add_moveline_in_done_move_1(self):
        product = self.product_fifo

        move1 = self._make_in_move(product, 10, 10)

        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_qty, 10.0)

        self.assertEqual(len(move1.move_line_ids), 1)
        self._set_quantity(move1, 20)
        self.assertEqual(move1.value, 200.0)
        self.assertEqual(move1.remaining_qty, 20.0)
        self.assertEqual(len(move1.move_line_ids), 2)

        self.assertEqual(product.qty_available, 20)
        self.assertEqual(product.total_value, 200)

        closing_move = self.env["account.move"].browse(
            move1.company_id.action_close_stock_valuation()["res_id"]
        )
        credit_line = closing_move.line_ids.filtered(lambda l: l.credit > 0)
        self.assertEqual(len(credit_line), 1)
        self.assertEqual(credit_line.debit, 0.0)
        self.assertEqual(credit_line.credit, 200.0)

        debit_line = closing_move.line_ids.filtered(lambda l: l.debit > 0)
        self.assertEqual(len(debit_line), 1)
        self.assertEqual(debit_line.debit, 200.0)
        self.assertEqual(debit_line.credit, 0.0)

    def test_fifo_edit_done_move1(self):
        product = self.product_fifo

        move1 = self._make_in_move(product, 10, 10)

        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_qty, 10.0)
        self.assertAlmostEqual(product.qty_available, 10.0)
        self.assertEqual(product.total_value, 100)

        closing_move = self._close()
        variation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_variation
        )
        valuation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_valuation
        )
        self.assertRecordValues(
            valuation_aml + variation_aml,
            [
                {
                    "account_id": self.account_stock_valuation.id,
                    "debit": 100,
                    "credit": 0,
                },
                {
                    "account_id": self.account_stock_variation.id,
                    "debit": 0,
                    "credit": 100,
                },
            ],
        )

        move2 = self._make_in_move(product, 10, 12)

        self.assertEqual(move2.value, 120.0)
        self.assertEqual(move2.remaining_qty, 10.0)
        self.assertEqual(move2._get_price_unit(), 12.0)
        self.assertAlmostEqual(product.qty_available, 20.0)
        self.assertAlmostEqual(product.qty_available, 20.0)
        self.assertEqual(product.total_value, 220)

        closing_move = self._close()
        variation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_variation
        )
        valuation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_valuation
        )
        self.assertRecordValues(
            valuation_aml + variation_aml,
            [
                {
                    "account_id": self.account_stock_valuation.id,
                    "debit": 120,
                    "credit": 0,
                },
                {
                    "account_id": self.account_stock_variation.id,
                    "debit": 0,
                    "credit": 120,
                },
            ],
        )

        move3 = self._make_out_move(product, 8)

        self.assertEqual(move3.value, 80.0)
        self.assertEqual(move3.remaining_qty, 0.0)
        self.assertAlmostEqual(product.qty_available, 12.0)
        self.assertAlmostEqual(product.qty_available, 12.0)
        self.assertEqual(product.total_value, 140)
        closing_move = self._close()
        variation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_variation
        )
        valuation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_valuation
        )
        self.assertRecordValues(
            valuation_aml + variation_aml,
            [
                {
                    "account_id": self.account_stock_valuation.id,
                    "debit": 0,
                    "credit": 80,
                },
                {
                    "account_id": self.account_stock_variation.id,
                    "debit": 80,
                    "credit": 0,
                },
            ],
        )

        move3.quantity = 14
        self.assertEqual(move3.product_qty, 8)
        self.assertEqual(move3.value, 140)

        self.assertEqual(product.total_value, 72)
        closing_move = self._close()
        variation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_variation
        )
        valuation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_valuation
        )
        self.assertRecordValues(
            valuation_aml + variation_aml,
            [
                {
                    "account_id": self.account_stock_valuation.id,
                    "debit": 0,
                    "credit": 68,
                },
                {
                    "account_id": self.account_stock_variation.id,
                    "debit": 68,
                    "credit": 0,
                },
            ],
        )

        self.assertEqual(product.qty_available, 6)
        self.assertAlmostEqual(product.qty_available, 6.0)
        self.assertEqual(product.total_value, 72)
        self.assertEqual(
            sum(self._get_stock_valuation_move_lines().mapped("balance")), 72
        )

    def test_fifo_edit_done_move2(self):
        product = self.product_fifo

        move1 = self._make_in_move(product, 10, 10)

        self.assertEqual(move1.value, 100.0)
        self.assertEqual(move1.remaining_qty, 10.0)

        move2 = self._make_out_move(product, 10)

        self.assertEqual(move2.value, 100.0)
        self.assertEqual(move2.remaining_qty, 0.0)

        move2.quantity = 8

        self.assertEqual(move2.value, 80.0)

        self.assertEqual(product.qty_available, 2)

        move2.quantity = 10

        self.assertEqual(move2.value, 100.0)
        self.assertEqual(product.qty_available, 0)
        self.assertEqual(product.total_value, 0)

    def test_fifo_standard_price_upate_1(self):
        product = self.product_fifo
        self._make_in_move(product, 3, unit_cost=17)
        self._make_in_move(product, 1, unit_cost=23)
        self.assertEqual(product.standard_price, 18.5)
        self._make_out_move(product, 3)
        self.assertEqual(product.standard_price, 23)

    def test_fifo_standard_price_upate_2(self):
        product = self.product_fifo
        self._make_in_move(product, 5, unit_cost=17)
        self._make_in_move(product, 1, unit_cost=23)
        self.assertEqual(product.standard_price, 18)
        self._make_out_move(product, 4)
        self.assertEqual(product.standard_price, 20)

    def test_fifo_standard_price_upate_3(self):
        product = self.product_fifo
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
        product = self.product_avco
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 8.0,
                "price_unit": 1,
                "state": "done",
                "move_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "location_id": self.supplier_location.id,
                            "location_dest_id": self.stock_location.id,
                            "product_uom_id": self.uom.id,
                            "quantity": 8.0,
                            "state": "done",
                        },
                    )
                ],
            }
        )
        move1.value_manual = 8.0
        self.assertEqual(product.qty_available, 8.0)
        self.assertEqual(product.total_value, 8.0)

    def test_average_perpetual_1(self):
        product = self.product_avco

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 60.0,
                "price_unit": 15,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 60.0
        move1.picked = True
        move1._action_done()
        move1.value_manual = 900

        self.assertEqual(move1.value, 900.0)

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 140.0,
                "price_unit": 15.50,
            }
        )
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 140.0
        move2.picked = True
        move2._action_done()
        move2.value_manual = 2170

        self.assertEqual(move2.value, 2170.0)

        move3 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 190.0,
            }
        )
        move3._action_confirm()
        move3._action_assign()
        move3.move_line_ids.quantity = 190.0
        move3.picked = True
        move3._action_done()

        self.assertEqual(move3.value, 2916.5)

        move4 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 70.0,
                "price_unit": 16.00,
            }
        )
        move4._action_confirm()
        move4._action_assign()
        move4.move_line_ids.quantity = 70.0
        move4.picked = True
        move4._action_done()
        move4.value_manual = 1120

        self.assertEqual(move4.value, 1120.0)

        move5 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 30.0,
            }
        )
        move5._action_confirm()
        move5._action_assign()
        move5.move_line_ids.quantity = 30.0
        move5.picked = True
        move5._action_done()

        self.assertEqual(move5.value, 477.56)

        move6 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 10.0,
                "price_unit": 99,
            }
        )
        move6._action_confirm()
        move6._action_assign()
        move6.move_line_ids.owner_id = self.owner.id
        move6.move_line_ids.quantity = 10.0
        move6.picked = True
        move6._action_done()
        move6.value_manual = 990

        self.assertEqual(move6.value, 0)

        move7 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 50.0,
            }
        )
        move7._action_confirm()
        move7._action_assign()
        move7.move_line_ids.quantity = 50.0
        move7.picked = True
        move7._action_done()

        self.assertEqual(move7.value, 795.94)
        self.assertAlmostEqual(product.qty_available, 10)
        self.assertAlmostEqual(product.total_value, 0.0)

    def test_average_perpetual_2(self):
        product = self.product_avco
        self._make_in_move(product, 10, 10)
        self.assertEqual(product.standard_price, 10)

        move2 = self._make_in_move(product, 10, 15)
        self.assertEqual(product.standard_price, 12.5)

        self._make_out_move(product, 15)
        self.assertEqual(product.standard_price, 12.5)

        self._make_out_move(product, 10)
        self.assertEqual(product.standard_price, 12.5)
        self.assertEqual(product.qty_available, -5)
        self.assertEqual(product.total_value, -62.5)

        self._set_quantity(move2, 20)

        self.assertEqual(product.qty_available, 5)
        self.assertEqual(product.total_value, 66.67)
        self.assertAlmostEqual(product.standard_price, 13.3333333)

    def test_average_perpetual_3(self):
        product = self.product_avco

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 10.0,
                "price_unit": 10,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 10.0
        move1.picked = True
        move1._action_done()
        move1.value_manual = 100.0

        self.assertEqual(product.qty_available, 10.0)
        self.assertEqual(product.total_value, 100.0)
        product._invalidate_cache()

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 10.0,
                "price_unit": 15,
            }
        )
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 10.0
        move2.picked = True
        move2._action_done()
        move2.value_manual = 150.0

        self.assertEqual(product.qty_available, 20.0)
        self.assertEqual(product.total_value, 250.0)
        product._invalidate_cache()

        move3 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 15.0,
            }
        )
        move3._action_confirm()
        move3._action_assign()
        move3.move_line_ids.quantity = 15.0
        move3.picked = True
        move3._action_done()

        self.assertEqual(product.qty_available, 5.0)
        self.assertEqual(product.total_value, 62.5)
        product._invalidate_cache()

        move4 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 10.0,
            }
        )
        move4._action_confirm()
        move4._action_assign()
        move4.move_line_ids.quantity = 10.0
        move4.picked = True
        move4._action_done()

        self.assertEqual(product.qty_available, -5.0)
        self.assertEqual(product.total_value, -62.5)
        product._invalidate_cache()

        move2.move_line_ids.quantity = 0
        self.assertEqual(product.qty_available, -15.0)

    def test_average_perpetual_4(self):
        product = self.product_avco

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 1.0,
                "price_unit": 10,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 1.0
        move1.picked = True
        move1._action_done()
        move1.value_manual = 10.0

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 3.0,
                "price_unit": 5,
            }
        )
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 1.0
        move2.picked = True
        move2._action_done()
        move2.value_manual = 5.0

        self.assertAlmostEqual(product.qty_available, 2.0)
        self.assertAlmostEqual(product.standard_price, 7.5)

    def test_average_perpetual_5(self):
        product = self.product_avco

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 1.0,
                "price_unit": 10,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 1.0
        move1.move_line_ids.owner_id = self.owner.id
        move1.picked = True
        move1._action_done()
        move1.value_manual = 10.0

        self.assertAlmostEqual(move1.remaining_qty, 0.0)
        self.assertAlmostEqual(product.qty_available, 1.0)
        self.assertAlmostEqual(product.total_value, 0.0)

    def test_average_perpetual_6(self):
        product = self.product_avco

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 1.0,
                "price_unit": 10,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 1.0
        move1.picked = True

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 1.0,
                "price_unit": 5,
            }
        )
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 1.0
        move2.picked = True

        (move1 | move2)._action_done()
        move1.value_manual = 10.0
        move2.value_manual = 5.0

        self.assertAlmostEqual(product.standard_price, 7.5)
        self.assertEqual(product.qty_available, 2)
        self.assertEqual(product.total_value, 15)

    def test_average_perpetual_7(self):
        product = self.product_avco

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 5,
                "price_unit": 10,
            }
        )
        move1._action_confirm()
        move1.quantity = 5
        move1.picked = True
        move1._action_done()
        move1.value_manual = 50.0

        self.assertAlmostEqual(product.standard_price, 10)
        self.assertAlmostEqual(move1.value, 50)
        self.assertAlmostEqual(product.qty_available, 5)
        self.assertAlmostEqual(product.total_value, 50)
        product._invalidate_cache()

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 10,
                "price_unit": 20,
            }
        )
        move2._action_confirm()
        move2.quantity = 10
        move2.picked = True
        move2._action_done()
        move2.value_manual = 200.0

        self.assertAlmostEqual(product.standard_price, 16.66666667)
        self.assertAlmostEqual(move2.value, 200)
        self.assertAlmostEqual(product.qty_available, 15)
        self.assertAlmostEqual(product.total_value, 250)
        product._invalidate_cache()

        self._set_quantity(move1, 15)

        self.assertAlmostEqual(product.standard_price, 14.0)
        self.assertAlmostEqual(product.qty_available, 25)
        self.assertAlmostEqual(product.total_value, 350)

    def test_average_perpetual_8(self):
        product = self.product_avco

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 1,
                "price_unit": 10,
            }
        )
        move1._action_confirm()
        move1.quantity = 1
        move1.picked = True
        move1._action_done()
        move1.value_manual = 10.0

        self.assertAlmostEqual(product.standard_price, 10)

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 1,
                "price_unit": 20,
            }
        )
        move2._action_confirm()
        move2.quantity = 1
        move2.picked = True
        move2._action_done()

        self.assertAlmostEqual(product.standard_price, 10.0)

        move3 = self.env["stock.move"].create(
            {
                "location_id": self.customer_location.id,
                "location_dest_id": self.supplier_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 1,
                "price_unit": 20,
            }
        )
        move3._action_confirm()
        move3.quantity = 1
        move3.picked = True
        move3._action_done()

        self.assertAlmostEqual(product.standard_price, 10.0)

    def test_average_perpetual_9(self):
        product = self.product_avco
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 10,
                "price_unit": 10,
            }
        )
        move1._action_confirm()
        move1.picked = True
        move1._action_done()
        move1.value_manual = 100.0

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 15.0,
            }
        )
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 15.0
        move2.picked = True
        move2._action_done()

        move1.move_line_ids.quantity = 15

    def test_average_stock_user(self):
        product = self.product_avco
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 10,
                "price_unit": 10,
            }
        )
        move1._action_confirm()
        move1.picked = True
        move1._action_done()

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 15.0,
            }
        )
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 15.0
        move2.picked = True
        move2.with_user(self.inventory_user)._action_done()

    def test_average_negative_1(self):
        product = self.product_avco_auto

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 10.0,
                "price_unit": 10,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 10.0
        move1.picked = True
        move1._action_done()
        move1.value_manual = 100.0

        self._create_bill(product, 10, 10)

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 20.0,
            }
        )
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 20.0
        move2.picked = True
        move2._action_done()

        self._create_invoice(product, 20, 10)
        valuation_aml = self._get_stock_valuation_move_lines()
        move2_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 2)
        self.assertEqual(move2_valuation_aml.debit, 0)
        self.assertEqual(move2_valuation_aml.credit, 200)

        self._set_quantity(move2, 10.0)
        self._create_bill(product, 10, 10)

        valuation_aml = self._get_stock_valuation_move_lines()
        move2_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 3)
        self.assertEqual(move2_valuation_aml.debit, 100)
        self.assertEqual(move2_valuation_aml.credit, 0)

        self._set_quantity(move2, 11.0)
        self._create_invoice(product, 1, 10)

        valuation_aml = self._get_stock_valuation_move_lines()
        move2_valuation_aml = valuation_aml[-1]
        self.assertEqual(len(valuation_aml), 4)
        self.assertEqual(move2_valuation_aml.debit, 0)
        self.assertEqual(move2_valuation_aml.credit, 10)

    def test_average_negative_2(self):
        product = self.product_avco

        product.standard_price = 99

        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                product, self.stock_location
            ),
            0,
        )
        move1 = self._make_out_move(product, 10, force_assign=True)
        self.assertEqual(move1.value, 990)
        self.assertEqual(product.qty_available, -10)
        self.assertEqual(product.total_value, -990.0)

    def test_average_negative_3(self):
        product = self.product_avco_auto

        with freeze_time(Datetime.now() - timedelta(days=10)):
            product.standard_price = 99

        move1 = self._make_in_move(product, 10, 10)

        self.assertEqual(move1.value, 100)
        self.assertEqual(product.qty_available, 10)
        self.assertEqual(product.total_value, 100)

        move2 = self._make_out_move(product, 10)

        self.assertEqual(move2.value, 100.0)
        self.assertEqual(move2.remaining_qty, 0.0)
        product._invalidate_cache()

        move3 = self._make_out_move(product, 10)
        move3._action_done()

        self.assertEqual(move3.value, 100.0)

    def test_average_negative_4(self):
        product = self.product_avco

        product.standard_price = 99

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 10.0,
                "price_unit": 10,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 10.0
        move1.picked = True
        move1._action_done()
        move1.value_manual = 100.0

        self.assertEqual(move1.value, 100.0)

    def test_average_negative_5(self):
        product = self.product_avco

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 10.0,
                "price_unit": 10,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 10.0
        move1.picked = True
        move1._action_done()
        move1.value_manual = 100.0

        self.assertEqual(move1.value, 100.0)
        self.assertEqual(product.standard_price, 10)

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 10.0,
                "price_unit": 20,
            }
        )
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 10.0
        move2.picked = True
        move2._action_done()
        move2.value_manual = 200.0

        self.assertEqual(move2.value, 200.0)
        self.assertEqual(product.standard_price, 15)

        move3 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 5.0,
            }
        )
        move3._action_confirm()
        move3.quantity = 5.0
        move3.picked = True
        move3._action_done()

        self.assertEqual(move3.value, 75.0)
        self.assertEqual(product.standard_price, 15)

        move4 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 30.0,
            }
        )
        move4._action_confirm()
        move4.quantity = 30.0
        move4.picked = True
        move4._action_done()

        self.assertEqual(move4.value, 450.0)
        self.assertEqual(product.standard_price, 15)

        move5 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 20.0,
                "price_unit": 20,
            }
        )
        move5._action_confirm()
        move5._action_assign()
        move5.move_line_ids.quantity = 20.0
        move5.picked = True
        move5._action_done()
        move5.value_manual = 400.0
        self.assertEqual(move5.value, 400.0)

        self.assertEqual(move4.value, 450)

        self.assertEqual(product.qty_available, 5)
        self.assertEqual(product.total_value, 100)
        self.assertEqual(product.standard_price, 20)

        move6 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 5.0,
            }
        )
        move6._action_confirm()
        move6.quantity = 5.0
        move6.picked = True
        move6._action_done()

        self.assertEqual(move6.value, 100.0)
        self.assertEqual(product.standard_price, 20)

        move7 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 10.0,
                "price_unit": 10,
            }
        )
        move7._action_confirm()
        move7._action_assign()
        move7.move_line_ids.quantity = 10.0
        move7.picked = True
        move7._action_done()
        move7.value_manual = 100.0

        self.assertEqual(move7.value, 100.0)
        self.assertEqual(product.standard_price, 10)

    def test_average_automated_with_cost_change(self):
        product = self.product_avco
        product.categ_id.property_valuation = "real_time"

        product.standard_price = 100
        move1 = self._make_out_move(product, 10, force_assign=True)

        self.assertAlmostEqual(product.qty_available, -10.0)
        self.assertEqual(move1.value, 1000.0)
        self.assertAlmostEqual(product.total_value, -1000.0)

        product.standard_price = 10
        self.assertEqual(product.total_value, -100.0)

        inventory_location = product.property_stock_inventory
        inventory_location.company_id = self.env.company.id

        move2 = self.env["stock.move"].create(
            {
                "location_id": inventory_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 10.0,
            }
        )
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 10.0
        move2.picked = True
        move2._action_done()

        self.assertAlmostEqual(product.qty_available, 0.0)
        self.assertAlmostEqual(move2.value, 100.0)

        self.assertAlmostEqual(product.total_value, 0.0)

    def test_average_manual_1(self):
        product = self.product_avco

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 1.0,
                "price_unit": 10,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 1.0
        move1.move_line_ids.owner_id = self.owner.id
        move1.picked = True
        move1._action_done()

        self.assertAlmostEqual(move1.remaining_qty, 0.0)
        self.assertAlmostEqual(product.qty_available, 1.0)
        self.assertAlmostEqual(product.total_value, 0.0)

    def test_standard_perpetual_1(self):
        product = self.product_standard_auto

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 1.0,
                "price_unit": 10,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 1.0
        move1.move_line_ids.owner_id = self.owner.id
        move1.picked = True
        move1._action_done()

        self.assertAlmostEqual(move1.remaining_qty, 0.0)
        self.assertAlmostEqual(product.qty_available, 1.0)
        self.assertAlmostEqual(product.total_value, 0.0)

    def test_standard_manual_1(self):
        product = self.product_standard

        move1 = self._make_in_move(product, 1, 10, owner_id=self.owner.id)

        self.assertAlmostEqual(move1.remaining_qty, 0.0)
        self.assertAlmostEqual(product.qty_available, 1.0)
        self.assertAlmostEqual(product.total_value, 0.0)

    def test_standard_manual_2(self):
        product = self.product_standard

        product.standard_price = 10.0

        move1 = (
            self.env["stock.move"]
            .with_user(self.inventory_user)
            .create(
                {
                    "location_id": self.supplier_location.id,
                    "location_dest_id": self.stock_location.id,
                    "product_id": product.id,
                    "product_uom_id": self.uom.id,
                    "product_uom_qty": 10.0,
                }
            )
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 10.0
        move1.picked = True
        move1._action_done()

    def test_standard_perpetual_2(self):
        product = self.product_standard
        product.categ_id.property_valuation = "real_time"

        product.standard_price = 10.0

        move1 = (
            self.env["stock.move"]
            .with_user(self.inventory_user)
            .create(
                {
                    "location_id": self.supplier_location.id,
                    "location_dest_id": self.stock_location.id,
                    "product_id": product.id,
                    "product_uom_id": self.uom.id,
                    "product_uom_qty": 10.0,
                }
            )
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 10.0
        move1.picked = True
        move1._action_done()

    def test_change_cost_method_1(self):
        product = self.product_fifo

        self._make_in_move(product, 10, 10)

        self._make_in_move(product, 10, 15)

        self._make_out_move(product, 1)

        self.assertAlmostEqual(product.qty_available, 19)
        self.assertEqual(product.total_value, 240)

        self.category_fifo.property_cost_method = "average"

        self.assertAlmostEqual(product.qty_available, 19)
        self.assertAlmostEqual(product.total_value, 237.5)

        self.assertEqual(product.standard_price, 12.5)

    def test_change_cost_method_2(self):
        product = self.product_fifo

        self._make_in_move(product, 10, 10)

        self._make_in_move(product, 10, 15)

        self._make_out_move(product, 1)

        self.assertAlmostEqual(product.qty_available, 19)
        self.assertEqual(product.total_value, 240)

        product.categ_id = self.category_standard

        self.assertAlmostEqual(product.total_value, 240, delta=0.04)
        self.assertAlmostEqual(product.qty_available, 19)

        self.assertAlmostEqual(product.standard_price, 12.6315789)

    def test_fifo_sublocation_valuation_1(self):
        product = self.product_fifo
        product.standard_price = 10

        view_location = self.env["stock.location"].create(
            {"name": "view", "usage": "view"}
        )
        subloc1 = self.env["stock.location"].create(
            {
                "name": "internal",
                "usage": "internal",
                "location_id": view_location.id,
            }
        )
        subloc2 = self.env["stock.location"].create(
            {
                "name": "scrap",
                "usage": "inventory",
                "location_id": view_location.id,
            }
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 2.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.write(
            {
                "move_line_ids": [
                    (5, 0, 0),
                    (
                        0,
                        None,
                        {
                            "product_id": product.id,
                            "quantity": 1,
                            "location_id": self.supplier_location.id,
                            "location_dest_id": subloc1.id,
                            "product_uom_id": self.uom.id,
                        },
                    ),
                    (
                        0,
                        None,
                        {
                            "product_id": product.id,
                            "quantity": 1,
                            "location_id": self.supplier_location.id,
                            "location_dest_id": subloc2.id,
                            "product_uom_id": self.uom.id,
                        },
                    ),
                ]
            }
        )
        move1.picked = True
        move1._action_done()
        self.assertEqual(move1.value, 10)
        self.assertEqual(move1.remaining_qty, 1)
        self.assertAlmostEqual(product._with_valuation_context().qty_available, 1.0)
        self.assertEqual(product.total_value, 10)

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 2.0,
            }
        )
        move2._action_confirm()
        move2._action_assign()

        move2.write(
            {
                "move_line_ids": [
                    (5, 0, 0),
                    (
                        0,
                        None,
                        {
                            "product_id": product.id,
                            "quantity": 1,
                            "location_id": subloc1.id,
                            "location_dest_id": self.supplier_location.id,
                            "product_uom_id": self.uom.id,
                        },
                    ),
                    (
                        0,
                        None,
                        {
                            "product_id": product.id,
                            "quantity": 1,
                            "location_id": subloc2.id,
                            "location_dest_id": self.supplier_location.id,
                            "product_uom_id": self.uom.id,
                        },
                    ),
                ]
            }
        )
        move2.picked = True
        move2._action_done()
        self.assertEqual(move2.value, 10)
        self.assertEqual(move1.remaining_qty, 0)
        self.assertAlmostEqual(product.qty_available, 0.0)
        self.assertEqual(product.total_value, 0)

    def test_move_in_or_out(self):
        product = self.product_standard
        scrap = self.env["stock.location"].create(
            {
                "name": "scrap",
                "usage": "inventory",
                "location_id": self.stock_location.id,
            }
        )

        move1 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 2.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.write(
            {
                "move_line_ids": [
                    (
                        0,
                        None,
                        {
                            "product_id": product.id,
                            "quantity": 1,
                            "location_id": self.stock_location.id,
                            "location_dest_id": self.stock_location.id,
                            "product_uom_id": self.uom.id,
                        },
                    ),
                    (
                        0,
                        None,
                        {
                            "product_id": product.id,
                            "quantity": 1,
                            "location_id": self.stock_location.id,
                            "location_dest_id": scrap.id,
                            "product_uom_id": self.uom.id,
                        },
                    ),
                ]
            }
        )
        move1.picked = True
        self.assertEqual(move1._is_out(), True)

        customer1 = self.env["stock.location"].create(
            {
                "name": "customer",
                "usage": "customer",
                "location_id": self.stock_location.id,
            }
        )
        self.env["stock.location"].create(
            {
                "name": "supplier",
                "usage": "supplier",
                "location_id": self.stock_location.id,
            }
        )
        move2 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 2.0,
            }
        )
        move2._action_confirm()
        move2._action_assign()
        move2.write(
            {
                "move_line_ids": [
                    (
                        0,
                        None,
                        {
                            "product_id": product.id,
                            "quantity": 1,
                            "location_id": customer1.id,
                            "location_dest_id": self.stock_location.id,
                            "product_uom_id": self.uom.id,
                        },
                    ),
                    (
                        0,
                        None,
                        {
                            "product_id": product.id,
                            "quantity": 1,
                            "location_id": self.stock_location.id,
                            "location_dest_id": customer1.id,
                            "product_uom_id": self.uom.id,
                        },
                    ),
                ]
            }
        )
        move2.picked = True
        self.assertEqual(move2._is_in(), True)
        self.assertEqual(move2._is_out(), True)

    def test_at_date_standard_1(self):
        product = self.product_standard

        now = Datetime.now()
        date1 = now - timedelta(days=8)
        date2 = now - timedelta(days=7)
        date3 = now - timedelta(days=6)
        date4 = now - timedelta(days=5)
        date5 = now - timedelta(days=4)
        date6 = now - timedelta(days=3)
        date7 = now - timedelta(days=2)
        date8 = now - timedelta(days=1)

        with freeze_time(date1 - timedelta(hours=1)):
            product.standard_price = 5.0
        with freeze_time(date1):
            product.standard_price = 10.0

        with freeze_time(date2):
            self._make_in_move(product, 10)

        self.assertEqual(product.qty_available, 10)
        self.assertEqual(product.total_value, 100)

        with freeze_time(date3):
            self._make_in_move(product, 20)

        self.assertEqual(product.qty_available, 30)
        self.assertEqual(product.total_value, 300)

        with freeze_time(date4):
            self._make_out_move(product, 15)

        self.assertEqual(product.qty_available, 15)
        self.assertEqual(product.total_value, 150)

        with freeze_time(date5):
            product.standard_price = 5

        self.assertEqual(product.qty_available, 15)
        self.assertEqual(product.total_value, 75)

        with freeze_time(date6):
            self._make_out_move(product, 10)

        self.assertEqual(product.qty_available, 5)
        self.assertEqual(product.total_value, 25.0)

        with freeze_time(date7):
            product.standard_price = 7.5

        with freeze_time(date8):
            self._make_in_move(product, 90)

        self.assertEqual(product.qty_available, 95)
        self.assertEqual(product.total_value, 712.5)

        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date1)).qty_available, 0
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date2)).qty_available, 10
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date3)).qty_available, 30
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date4)).qty_available, 15
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date5)).qty_available, 15
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date6)).qty_available, 5
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date7)).qty_available, 5
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date8)).qty_available, 95
        )

        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date1)).total_value, 0
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date2)).total_value, 100
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date3)).total_value, 300
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date4)).total_value, 150
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date5)).total_value, 75
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date6)).total_value, 25
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date8)).total_value, 712.5
        )

    def test_at_date_fifo_1(self):
        product = self.product_fifo

        now = Datetime.now()
        date1 = now - timedelta(days=8)
        date2 = now - timedelta(days=7)
        date3 = now - timedelta(days=6)
        date4 = now - timedelta(days=5)
        date5 = now - timedelta(days=4)
        date6 = now - timedelta(days=3)

        with freeze_time(date1):
            move1 = self._make_in_move(product, 10, 10)

        self.assertEqual(product.qty_available, 10)
        self.assertEqual(product.total_value, 100)

        with freeze_time(date2):
            self._make_in_move(product, 10, 12)

        self.assertAlmostEqual(product.qty_available, 20)
        self.assertEqual(product.total_value, 220)

        with freeze_time(date3):
            self._make_out_move(product, 15)

        self.assertAlmostEqual(product.qty_available, 5.0)
        self.assertEqual(product.total_value, 60)

        with freeze_time(date4):
            self._make_out_move(product, 20)

        self.assertAlmostEqual(product.qty_available, -15.0)
        self.assertEqual(product.total_value, -180)

        with freeze_time(date5):
            self._make_in_move(product, 100, 15)

        self.assertEqual(product.qty_available, 85)
        self.assertEqual(product.total_value, 1275)

        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date1)).qty_available, 10
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date1)).total_value, 100
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date2)).qty_available, 20
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date2)).total_value, 220
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date3)).qty_available, 5
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date3)).total_value, 60
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date4)).qty_available, -15
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date4)).total_value, -180
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date5)).qty_available, 85
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date5)).total_value, 1275
        )

        with freeze_time(date6):
            self._set_quantity(move1, 20)
        self.assertEqual(product.qty_available, 95)
        self.assertEqual(product.total_value, 1425)

        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date1)).qty_available, 20
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date1)).total_value, 100
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date2)).qty_available, 30
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date2)).total_value, 220
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date3)).qty_available, 15
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date3)).total_value, 145
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date4)).qty_available, -5
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date4)).total_value, -60
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date5)).qty_available, 95
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date5)).total_value, 1425
        )

    def test_inventory_fifo_1(self):
        product = self.product_fifo
        product.standard_price = 15
        inventory_location = product.property_stock_inventory
        inventory_location.company_id = self.env.company.id

        move1 = self.env["stock.move"].create(
            {
                "location_id": inventory_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 12.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 12.0
        move1.picked = True
        move1._action_done()
        move1.value_manual = 180.0

        self.assertAlmostEqual(move1.value, 180.0)
        self.assertAlmostEqual(move1.remaining_qty, 12.0)
        self.assertAlmostEqual(product.total_value, 180.0)
        product._invalidate_cache()

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 12.0,
            }
        )
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 12.0
        move2.picked = True
        move2._action_done()

        move1._invalidate_cache()
        self.assertAlmostEqual(move1.remaining_qty, 0.0)
        self.assertAlmostEqual(product.total_value, 0.0)

    def test_at_date_average_1(self):
        now = Datetime.now()
        date1 = now - timedelta(days=8)
        date2 = now - timedelta(days=7)

        product = self.product_avco
        product.standard_price = 10
        product = self.product_avco
        inventory_location = product.property_stock_inventory
        inventory_location.company_id = self.env.company.id

        move1 = self.env["stock.move"].create(
            {
                "location_id": inventory_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 10.0,
            }
        )
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.quantity = 10.0
        move1.picked = True
        move1._action_done()
        move1.date = date1

        move2 = self.env["stock.move"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": inventory_location.id,
                "product_id": product.id,
                "product_uom_id": self.uom.id,
                "product_uom_qty": 5.0,
            }
        )
        move2._action_confirm()
        move2._action_assign()
        move2.move_line_ids.quantity = 5.0
        move2.picked = True
        move2._action_done()
        move2.date = date2

        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date1)).qty_available, 10
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date1)).total_value, 100
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date2)).qty_available, 5
        )
        self.assertEqual(
            product.with_context(to_date=Datetime.to_string(date2)).total_value, 50
        )

    def test_forecast_report_value(self):
        product = self.product_standard
        currency_1 = self.env["res.currency"].create(
            {
                "name": "UNF",
                "symbol": "U",
                "rounding": 0.01,
                "currency_unit_label": "Unifranc",
                "rate": 1,
                "position": "before",
            }
        )
        currency_2 = self.env["res.currency"].create(
            {
                "name": "DBL",
                "symbol": "DD",
                "rounding": 0.01,
                "currency_unit_label": "Doublard",
                "rate": 2,
            }
        )
        company_form = Form(self.env["res.company"])
        company_form.name = "BB Inc."
        company_form.currency_id = currency_1
        company_1 = company_form.save()
        company_form = Form(self.env["res.company"])
        company_form.name = "BB Corp"
        company_form.currency_id = currency_2
        company_2 = company_form.save()
        warehouse_1 = self.env["stock.warehouse"].search(
            [("company_id", "=", company_1.id)], limit=1
        )
        warehouse_2 = self.env["stock.warehouse"].search(
            [("company_id", "=", company_2.id)], limit=1
        )
        stock_1 = warehouse_1.lot_stock_id
        stock_2 = warehouse_2.lot_stock_id
        self.env.user.company_ids += company_1
        self.env.user.company_ids += company_2
        product.with_company(company_1).standard_price = 10
        product.with_company(company_2).standard_price = 12

        move_1 = (
            self.env["stock.move"]
            .with_company(company_1)
            .create(
                {
                    "location_id": self.supplier_location.id,
                    "location_dest_id": stock_1.id,
                    "product_id": product.id,
                    "product_uom_id": self.uom.id,
                    "product_uom_qty": 5.0,
                }
            )
        )
        move_1._action_confirm()
        move_1.move_line_ids.quantity = 5.0
        move_1.picked = True
        move_1._action_done()

        move_2 = (
            self.env["stock.move"]
            .with_company(company_2)
            .create(
                {
                    "location_id": self.supplier_location.id,
                    "location_dest_id": stock_2.id,
                    "product_id": product.id,
                    "product_uom_id": self.uom.id,
                    "product_uom_qty": 4.0,
                }
            )
        )
        move_2._action_confirm()
        move_2.move_line_ids.quantity = 4.0
        move_2.picked = True
        move_2._action_done()

        report = self.env["stock.forecasted_product_product"]
        report_for_company_1 = report.with_company(company_1).with_context(
            warehouse_id=warehouse_1.id
        )
        report_for_company_2 = report.with_company(company_2).with_context(
            warehouse_id=warehouse_2.id
        )
        report_value_1 = report_for_company_1.get_report_values(docids=product.ids)
        report_value_2 = report_for_company_2.get_report_values(docids=product.ids)
        self.assertEqual(report_value_1["docs"]["value"], "U 50.00")
        self.assertEqual(report_value_2["docs"]["value"], "48.00 DD")

    def test_stock_report_avco_warehouse_dependency(self):
        self._use_multi_warehouses()
        product = self.product_avco_auto
        warehouse_1, warehouse_2 = self.warehouse, self.other_warehouse

        inventory_adjustment_loc = self.env["stock.location"].search(
            [("usage", "=", "inventory"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )
        self._make_in_move(
            product=product,
            quantity=15.0,
            location_id=inventory_adjustment_loc.id,
            location_dest_id=warehouse_1.lot_stock_id.id,
        )
        self._make_in_move(
            product=product,
            quantity=5.0,
            unit_cost=50,
            location_dest_id=warehouse_2.lot_stock_id.id,
        )
        self.assertRecordValues(
            product, [{"avg_cost": 20.0, "total_value": 400, "qty_available": 20}]
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_1.id),
            [{"avg_cost": 20.0, "total_value": 300, "qty_available": 15}],
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_2.id),
            [{"avg_cost": 20.0, "total_value": 100, "qty_available": 5}],
        )

        warehouse_3 = self.env["stock.warehouse"].create({"code": "WH-neg"})
        self._make_out_move(
            product=product, quantity=20.0, location_id=warehouse_3.lot_stock_id.id
        )
        self.assertRecordValues(
            product, [{"avg_cost": 20.0, "total_value": 0.0, "qty_available": 0.0}]
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_1.id),
            [{"avg_cost": 20.0, "total_value": 300, "qty_available": 15}],
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_2.id),
            [{"avg_cost": 20.0, "total_value": 100, "qty_available": 5}],
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_3.id),
            [{"avg_cost": 20.0, "total_value": -400, "qty_available": -20}],
        )

    def test_stock_report_fifo_warehouse_dependency(self):
        self._use_multi_warehouses()
        product = self.product_fifo_auto
        warehouse_1, warehouse_2 = self.warehouse, self.other_warehouse

        inventory_adjustment_loc = self.env["stock.location"].search(
            [("usage", "=", "inventory"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )
        self._make_in_move(
            product=product,
            quantity=15.0,
            location_id=inventory_adjustment_loc.id,
            location_dest_id=warehouse_1.lot_stock_id.id,
        )
        self._make_in_move(
            product=product,
            quantity=10.0,
            unit_cost=30,
            location_dest_id=warehouse_2.lot_stock_id.id,
        )
        self._make_out_move(
            product=product, quantity=5.0, location_id=warehouse_2.lot_stock_id.id
        )
        self.assertRecordValues(
            product, [{"avg_cost": 20.0, "total_value": 400, "qty_available": 20}]
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_1.id),
            [{"avg_cost": 20.0, "total_value": 300, "qty_available": 15}],
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_2.id),
            [{"avg_cost": 20.0, "total_value": 100, "qty_available": 5}],
        )

        warehouse_3 = self.env["stock.warehouse"].create({"code": "WH-neg"})
        self._make_out_move(
            product=product, quantity=20.0, location_id=warehouse_3.lot_stock_id.id
        )
        self.assertRecordValues(
            product, [{"avg_cost": 30.0, "total_value": 0.0, "qty_available": 0.0}]
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_1.id),
            [{"avg_cost": 30.0, "total_value": 450, "qty_available": 15}],
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_2.id),
            [{"avg_cost": 30.0, "total_value": 150, "qty_available": 5}],
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_3.id),
            [{"avg_cost": 30.0, "total_value": -600, "qty_available": -20}],
        )

    def test_stock_report_avco_lot_valuation_warehouse_dependency(self):
        self._use_multi_warehouses()
        product = self.product_avco_auto
        product.write(
            {
                "is_storable": True,
                "tracking": "lot",
                "lot_valuated": True,
            }
        )
        warehouse_1, warehouse_2 = self.warehouse, self.other_warehouse
        lots = self.env["stock.lot"].create(
            [
                {
                    "name": f"lot{i}",
                    "product_id": product.id,
                }
                for i in range(1, 4)
            ]
        )

        self._make_in_move(
            product=product,
            quantity=15.0,
            unit_cost=10,
            location_dest_id=warehouse_1.lot_stock_id.id,
            lot_ids=lots[0],
        )
        self._make_in_move(
            product=product,
            quantity=5.0,
            unit_cost=50,
            location_dest_id=warehouse_2.lot_stock_id.id,
            lot_ids=lots[0],
        )
        self._make_in_move(
            product=product,
            quantity=10.0,
            unit_cost=50,
            location_dest_id=warehouse_2.lot_stock_id.id,
            lot_ids=lots[1],
        )
        self.assertRecordValues(
            product, [{"avg_cost": 30.0, "total_value": 900, "qty_available": 30}]
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_1.id),
            [{"avg_cost": 20.0, "total_value": 300, "qty_available": 15}],
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_2.id),
            [{"avg_cost": 40.0, "total_value": 600, "qty_available": 15}],
        )
        warehouse_3 = self.env["stock.warehouse"].create(
            [
                {"name": "warehouse negative", "code": "WH-neg"},
            ]
        )
        self._make_out_move(
            product=product,
            quantity=30.0,
            location_id=warehouse_3.lot_stock_id.id,
            lot_ids=lots[2],
        )
        self.assertRecordValues(
            product, [{"avg_cost": 30.0, "total_value": 600.0, "qty_available": 0}]
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_1.id),
            [{"avg_cost": 20.0, "total_value": 300, "qty_available": 15.0}],
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_2.id),
            [{"avg_cost": 40.0, "total_value": 600, "qty_available": 15}],
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_3.id),
            [{"avg_cost": 10.0, "total_value": -300, "qty_available": -30}],
        )
        self.assertRecordValues(
            lots,
            [{"total_value": 400.0}, {"total_value": 500.0}, {"total_value": -300.0}],
        )
        self.assertRecordValues(
            lots.with_context(warehouse_id=warehouse_1.id),
            [{"total_value": 300.0}, {"total_value": 0.0}, {"total_value": 0.0}],
        )
        self.assertRecordValues(
            lots.with_context(warehouse_id=warehouse_2.id),
            [{"total_value": 100.0}, {"total_value": 500.0}, {"total_value": 0.0}],
        )
        self.assertRecordValues(
            lots.with_context(warehouse_id=warehouse_3.id),
            [{"total_value": 0.0}, {"total_value": 0.0}, {"total_value": -300.0}],
        )

        self._make_in_move(
            product=product,
            quantity=30.0,
            location_dest_id=warehouse_2.lot_stock_id.id,
            lot_ids=lots[2],
        )
        with freeze_time(Datetime.now() + timedelta(seconds=1)):
            product.standard_price = 10.0
        self.assertRecordValues(
            product, [{"avg_cost": 10.0, "total_value": 300.0, "qty_available": 30}]
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_1.id),
            [{"avg_cost": 10.0, "total_value": 150, "qty_available": 15.0}],
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_2.id),
            [{"avg_cost": 10.0, "total_value": 450, "qty_available": 45}],
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_3.id),
            [{"avg_cost": 10.0, "total_value": -300, "qty_available": -30}],
        )
        self.assertRecordValues(
            lots, [{"total_value": 200.0}, {"total_value": 100.0}, {"total_value": 0.0}]
        )
        self.assertRecordValues(
            lots.with_context(warehouse_id=warehouse_1.id),
            [{"total_value": 150.0}, {"total_value": 0.0}, {"total_value": 0.0}],
        )
        self.assertRecordValues(
            lots.with_context(warehouse_id=warehouse_2.id),
            [{"total_value": 50.0}, {"total_value": 100.0}, {"total_value": 300.0}],
        )
        self.assertRecordValues(
            lots.with_context(warehouse_id=warehouse_3.id),
            [{"total_value": 0.0}, {"total_value": 0.0}, {"total_value": -300.0}],
        )

    def test_stock_report_fifo_lot_valuation_warehouse_dependency(self):
        self._use_multi_warehouses()
        product = self.product_fifo_auto
        product.write(
            {
                "is_storable": True,
                "tracking": "lot",
                "lot_valuated": True,
            }
        )
        warehouse_1, warehouse_2 = self.warehouse, self.other_warehouse
        lots = self.env["stock.lot"].create(
            [
                {
                    "name": f"lot{i}",
                    "product_id": product.id,
                }
                for i in range(1, 3)
            ]
        )
        self._make_in_move(
            product=product,
            quantity=15.0,
            unit_cost=10,
            location_dest_id=warehouse_1.lot_stock_id.id,
            lot_ids=lots[0],
        )
        self._make_in_move(
            product=product,
            quantity=5.0,
            unit_cost=50,
            location_dest_id=warehouse_2.lot_stock_id.id,
            lot_ids=lots[0],
        )
        self._make_in_move(
            product=product,
            quantity=10.0,
            unit_cost=35,
            location_dest_id=warehouse_2.lot_stock_id.id,
            lot_ids=lots[1],
        )
        self.assertRecordValues(
            product, [{"avg_cost": 25.0, "total_value": 750, "qty_available": 30}]
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_1.id),
            [{"avg_cost": 20.0, "total_value": 300, "qty_available": 15}],
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_2.id),
            [{"avg_cost": 30.0, "total_value": 450, "qty_available": 15}],
        )
        warehouse_3 = self.env["stock.warehouse"].create(
            [
                {"name": "warehouse negative", "code": "WH-neg"},
            ]
        )
        self._make_out_move(
            product=product,
            quantity=8.0,
            location_id=warehouse_3.lot_stock_id.id,
            lot_ids=lots[0],
        )
        self._make_out_move(
            product=product,
            quantity=2.0,
            location_id=warehouse_2.lot_stock_id.id,
            lot_ids=lots[1],
        )
        lots.invalidate_recordset(["total_value"])
        self.assertRecordValues(
            product, [{"avg_cost": 30.0, "total_value": 600.0, "qty_available": 20.0}]
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_1.id),
            [{"avg_cost": 26.67, "total_value": 400, "qty_available": 15.0}],
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_2.id),
            [{"avg_cost": 31.79, "total_value": 413.33, "qty_available": 13}],
        )
        self.assertRecordValues(
            product.with_context(warehouse_id=warehouse_3.id),
            [{"avg_cost": 26.67, "total_value": -213.33, "qty_available": -8}],
        )
        self.assertRecordValues(lots, [{"total_value": 320.0}, {"total_value": 280.0}])
        self.assertRecordValues(
            lots.with_context(warehouse_id=warehouse_1.id),
            [{"total_value": 400.0}, {"total_value": 0.0}],
        )
        self.assertRecordValues(
            lots.with_context(warehouse_id=warehouse_2.id),
            [{"total_value": 133.33}, {"total_value": 280.0}],
        )
        self.assertRecordValues(
            lots.with_context(warehouse_id=warehouse_3.id),
            [{"total_value": -213.33}, {"total_value": 0.0}],
        )

    def test_fifo_and_sml_owned_by_company(self):
        product = self.product_fifo

        self.env["stock.picking"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "picking_type_id": self.env.ref("stock.picking_type_in").id,
                "owner_id": self.env.company.partner_id.id,
                "state": "draft",
            }
        )

        move = self._make_in_move(
            product, 1, 10, create_picking=True, owner=self.env.company.partner_id
        )

        closing_move = self.env["account.move"].browse(
            move.company_id.action_close_stock_valuation()["res_id"]
        )
        self.assertEqual(move.value, 10)
        self.assertEqual(closing_move.amount_total, 10)

    def test_create_receipts_different_uom(self):
        product = self.product_standard
        uom_dozen = self.env.ref("uom.product_uom_dozen")
        receipt = self.env["stock.picking"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "picking_type_id": self.picking_type_in.id,
                "owner_id": self.env.company.partner_id.id,
                "state": "draft",
            }
        )

        move = self.env["stock.move"].create(
            {
                "picking_id": receipt.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_id": uom_dozen.id,
                "product_uom_qty": 1.0,
                "price_unit": 10,
            }
        )
        receipt.action_confirm()
        move.quantity = 1
        move.picked = True
        receipt.button_validate()

        self.assertEqual(product.uom_name, "Units")
        self.assertEqual(product.qty_available, 12)
        move.quantity = 2
        self.assertEqual(product.qty_available, 24)

    def test_average_manual_price_change(self):
        product = self.product_avco

        self._make_in_move(product, 5, unit_cost=5)
        self._make_in_move(product, 2, unit_cost=6)

        self.assertEqual(
            self.env["stock.quant"].fields_get(["value"], ["aggregator"]),
            {"value": {"aggregator": "sum"}},
            "Field 'value' must be aggregatable.",
        )

        res = self.env["stock.quant"]._read_group(
            [("product_id", "=", product.id)], aggregates=["value:sum"]
        )
        self.assertEqual(res[0][0], 5 * 5 + 2 * 6)
        with freeze_time(Datetime.now() + timedelta(minutes=1)):
            product.standard_price = 7
        self.assertEqual(product.total_value, 49)

        with freeze_time(Datetime.now() + timedelta(minutes=2)):
            move = self._make_in_move(product, 5, unit_cost=5)
            move.sequence = -1

        with freeze_time(Datetime.now() + timedelta(minutes=3)):
            self.assertEqual(product.total_value, 74)

    def test_average_manual_revaluation(self):
        product = self.product_avco

        move1 = self._make_in_move(product, 1, unit_cost=20)
        move1.value_manual = 20
        move2 = self._make_in_move(product, 1, unit_cost=30)
        move2.value_manual = 30
        self.assertEqual(product.standard_price, 25)

        move2.value_manual = 20
        self.assertEqual(product.standard_price, 20)

    def test_fifo_manual_revaluation(self):
        product = self.product_fifo

        move1 = self._make_in_move(product, 1, unit_cost=15)
        move1.value_manual = 15
        move2 = self._make_in_move(product, 1, unit_cost=30)
        move2.value_manual = 30
        self.assertEqual(product.standard_price, 22.5)

        move2.value_manual = 20
        self.assertEqual(product.standard_price, 17.5)

    def test_manual_revaluation_statement(self):
        product = self.product_fifo
        product.categ_id.property_valuation = "real_time"

        move1 = self._make_in_move(product, 1, unit_cost=15)
        move1.value_manual = 15
        move1.value_manual = 25
        self.assertEqual(product.standard_price, 25.0)

    def test_journal_entries_from_change_product_cost_method(self):
        product = self.product_fifo_auto
        self._make_in_move(product, 10, 7.2)
        self._make_in_move(product, 20, 15.3)
        self._make_out_move(product, 100)
        product.categ_id = self.category_avco

        closing_move = self._close()
        valuation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_valuation
        )
        variation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_variation
        )

        self.assertRecordValues(
            valuation_aml + variation_aml,
            [
                {
                    "account_id": self.account_stock_valuation.id,
                    "debit": 0.0,
                    "credit": 882.0,
                },
                {
                    "account_id": self.account_stock_variation.id,
                    "debit": 882.0,
                    "credit": 0.0,
                },
            ],
        )

    def test_journal_entries_from_change_category(self):
        product = self.product_fifo
        other_categ = product.categ_id.copy(
            {
                "property_cost_method": "average",
            }
        )
        move1 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_qty": 10.0,
                "price_unit": 7.2,
            }
        )
        move2 = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_qty": 20.0,
                "price_unit": 15.3,
            }
        )
        (move1 + move2)._action_confirm()
        (move1 + move2)._action_assign()
        move1.quantity = 10
        move2.quantity = 20
        (move1 + move2).picked = True
        (move1 + move2)._action_done()
        move1.value_manual = 72.0
        move2.value_manual = 306.0
        move3 = self.env["stock.move"].create(
            {
                "product_id": product.id,
                "product_uom_qty": 100,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            }
        )
        move3._action_confirm()
        move3._action_assign()
        move3.quantity = 100
        move3.picked = True
        move3._action_done()
        product.product_tmpl_id.categ_id = other_categ

        closing_move = self.env["account.move"].browse(
            move3.company_id.action_close_stock_valuation()["res_id"]
        )
        valuation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_valuation
        )
        variation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_variation
        )

        self.assertRecordValues(
            valuation_aml + variation_aml,
            [
                {
                    "account_id": self.account_stock_valuation.id,
                    "debit": 0.0,
                    "credit": 882.0,
                },
                {
                    "account_id": self.account_stock_variation.id,
                    "debit": 882.0,
                    "credit": 0.0,
                },
            ],
        )

    def test_diff_uom_quantity_update_after_done(self):
        product = self.product_standard
        unit_uom = self.uom
        dozen_uom = self.env.ref("uom.product_uom_dozen")
        move = self.env["stock.move"].create(
            {
                "product_id": product.id,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": self.stock_location.id,
                "product_uom_id": unit_uom.id,
                "product_uom_qty": 12,
                "picking_type_id": self.picking_type_in.id,
            }
        )
        move._action_confirm()
        move._action_assign()
        move.move_line_ids = [
            Command.update(
                move.move_line_ids[0].id,
                {"quantity": 1, "product_uom_id": dozen_uom.id},
            )
        ]
        move.picked = True
        move._action_done()

        self.assertEqual(move.quantity, 12)
        self.assertEqual(move.value, 120)

        move.picking_id.action_toggle_is_locked()
        move.move_line_ids = [Command.update(move.move_line_ids[0].id, {"quantity": 2})]

        self.assertEqual(move.quantity, 24)

    def test_internal_location_with_no_company(self):
        product = self.product_standard
        location = self.env["stock.location"].create(
            {
                "name": "Internal no company",
                "usage": "internal",
                "company_id": False,
            }
        )
        self.assertFalse(location._is_valuation_required())

        move = self.env["stock.move"].create(
            {
                "product_id": product.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": location.id,
                "product_uom_qty": 1,
                "price_unit": 1,
            }
        )
        move._action_confirm()
        move._action_assign()
        move.quantity = 1
        move.picked = True
        move._action_done()

        self.assertEqual(move.state, "done")
        self.assertEqual(product.qty_available, 0)

    def test_stock_valuation_layer_revaluation_with_branch_company(self):
        product = self.product_avco

        self.assertEqual(product.standard_price, 10)
        self._make_in_move(product, 1, unit_cost=20)
        self.assertEqual(product.standard_price, 20)
        branch = self.env["res.company"].create(
            {
                "name": "Branch A",
                "parent_id": self.env.company.id,
            }
        )
        self.patch(self, "env", branch.with_company(branch).env)
        product.with_company(branch).categ_id.property_cost_method = "average"
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", branch.id)], limit=1
        )
        self._make_in_move(
            product,
            1,
            unit_cost=30,
            location_dest_id=warehouse.lot_stock_id.id,
            picking_type_id=warehouse.in_type_id.id,
        )
        self.assertEqual(product.with_company(branch).standard_price, 30)
        self.assertEqual(product.with_company(self.company).total_value, 20)
        self.assertEqual(product.with_company(branch).total_value, 30)

    def test_action_done_with_state_already_done(self):
        product = self.product_standard
        product.standard_price = 10

        in_move = self.env["stock.move"].create(
            {
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "product_id": product.id,
                "product_uom_qty": 10.0,
                "picked": True,
                "quantity": 10,
            }
        )
        in_move._action_done()
        self.assertEqual(in_move.state, "done")
        in_move._action_done()

        self.assertEqual(in_move.value, 100)
        self.assertEqual(in_move.quantity, 10)

    def test_scrap_reception_valuation(self):
        product = self.product_fifo
        product.product_tmpl_id.categ_id.property_valuation = "periodic"
        receipt = self._make_in_move(product, 10, 15, create_picking=True).picking_id
        scrap_location = self.env["stock.location"].search(
            [("name", "=", "Scrap"), ("company_id", "=", self.env.company.id)], limit=1
        )
        scrap_location.valuation_account_id = self.account_stock_variation
        scrap_form = Form(
            self.env["stock.scrap"].with_context(default_picking_id=receipt.id)
        )
        scrap_form.product_id = product
        scrap_form.scrap_qty = 2
        scrap = scrap_form.save()
        scrap.action_validate()
        self.assertRecordValues(
            receipt.move_ids,
            [
                {
                    "quantity": 10.0,
                    "remaining_qty": 8.0,
                    "value": 150.0,
                    "remaining_value": 120.0,
                },
                {
                    "quantity": 2.0,
                    "remaining_qty": 0.0,
                    "value": 30.0,
                    "remaining_value": 0.0,
                },
            ],
        )

    def test_positive_stock_adjustment_valuation(self):
        product = self.product_standard_auto
        accounts_data = product.product_tmpl_id._get_product_accounts()
        inventory_adjustment_loc = self.env["stock.location"].search(
            [("usage", "=", "inventory"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )
        inventory_adjustment_loc.valuation_account_id = self.account_stock_valuation
        product.standard_price = 10
        inventory_gain_move = self._make_in_move(
            product, 10, location_id=inventory_adjustment_loc.id
        )

        amls = inventory_gain_move.account_move_id.line_ids
        self.assertEqual(len(amls), 2)
        debit_line = amls.filtered(lambda l: l.debit > 0)
        credit_line = amls.filtered(lambda l: l.credit > 0)
        self.assertEqual(debit_line.account_id, accounts_data["stock_valuation"])
        self.assertEqual(credit_line.account_id, accounts_data["stock_valuation"])

    def test_negative_stock_adjustment_valuation(self):
        product = self.product_standard_auto
        accounts_data = product.product_tmpl_id._get_product_accounts()
        inventory_adjustment_loc = self.env["stock.location"].search(
            [("usage", "=", "inventory"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )
        inventory_adjustment_loc.valuation_account_id = self.account_stock_valuation
        product.standard_price = 10
        self._make_in_move(product, 10)
        inventory_loss_move = self._make_out_move(
            product, 5, location_dest_id=inventory_adjustment_loc.id
        )

        amls = inventory_loss_move.account_move_id.line_ids
        self.assertEqual(len(amls), 2)
        debit_line = amls.filtered(lambda l: l.debit > 0)
        credit_line = amls.filtered(lambda l: l.credit > 0)
        self.assertEqual(debit_line.account_id, accounts_data["stock_valuation"])
        self.assertEqual(credit_line.account_id, accounts_data["stock_valuation"])

    def test_valuation_rounding_method(self):
        uom_g = self.env.ref("uom.product_uom_gram")
        uom_kg = self.env.ref("uom.product_uom_kgm")
        product = self.product_standard
        product.uom_id = uom_kg

        receipt = self.env["stock.picking"].create(
            {
                "picking_type_id": self.picking_type_in.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.stock_location.id,
                "move_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_uom_id": uom_g.id,
                            "product_uom_qty": 11,
                            "quantity": 11,
                            "location_id": self.supplier_location.id,
                            "location_dest_id": self.stock_location.id,
                        }
                    )
                ],
            }
        )
        receipt.button_validate()

        self.assertEqual(receipt.move_ids.quantity, 11)
        self.assertAlmostEqual(receipt.move_ids.product_qty, 0.011)
        self.assertAlmostEqual(product.qty_available, 0.011)

        move_out = self._make_out_move(product, 11, uom_id=uom_g.id)

        self.assertEqual(move_out.quantity, 11)
        self.assertAlmostEqual(move_out.product_qty, 0.011)
        self.assertAlmostEqual(product.qty_available, 0.00)

    def test_stock_valuation_revaluation_avco(self):
        product = self.product_avco

        move_in_1 = self._make_in_move(product, 10, unit_cost=2)
        move_in_2 = self._make_in_move(product, 10, unit_cost=4)

        self.assertEqual(product.standard_price, 3)
        self.assertEqual(product.qty_available, 20)

        moves_in = move_in_1 | move_in_2
        self.assertEqual(sum(moves_in.mapped("remaining_value")), 60)

        with freeze_time(Datetime.now() + timedelta(seconds=1)):
            product.standard_price = 4

        self.assertEqual(product.standard_price, 4)
        self.assertEqual(product.qty_available, 20)

        std_price_history = self.env["product.value"].search(
            [("product_id", "=", product.id)],
            order="create_date desc, id desc",
            limit=1,
        )
        self.assertEqual(std_price_history.value, 4)

        self.assertEqual(sum(moves_in.mapped("remaining_value")), 80)

        closing_move = self._close()
        valuation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_valuation
        )
        variation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_variation
        )
        self.assertRecordValues(
            valuation_aml + variation_aml,
            [
                {
                    "account_id": self.account_stock_valuation.id,
                    "debit": 80,
                    "credit": 0,
                },
                {
                    "account_id": self.account_stock_variation.id,
                    "debit": 0,
                    "credit": 80,
                },
            ],
        )

    def test_stock_valuation_revaluation_avco_rounding(self):
        product = self.product_avco

        move1 = self._make_in_move(product, 1, unit_cost=1)
        move2 = self._make_in_move(product, 1, unit_cost=1)
        move3 = self._make_in_move(product, 1, unit_cost=1)
        moves = move1 | move2 | move3

        self.assertEqual(product.standard_price, 1)
        self.assertEqual(product.qty_available, 3)

        self.assertEqual(move1.remaining_value, 1)

        move1.value_manual = 2

        self.assertAlmostEqual(product.standard_price, 1.3333333)
        self.assertEqual(product.qty_available, 3)
        self.assertEqual(product.total_value, 4)

        self.assertEqual(sum(moves.mapped("remaining_value")), 3.99)
        self.assertEqual(move1.remaining_value, 1.33)

        closing_move = self._close()
        valuation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_valuation
        )
        variation_aml = closing_move.line_ids.filtered(
            lambda l: l.account_id == self.account_stock_variation
        )
        self.assertRecordValues(
            valuation_aml + variation_aml,
            [
                {
                    "account_id": self.account_stock_valuation.id,
                    "debit": 4,
                    "credit": 0,
                },
                {
                    "account_id": self.account_stock_variation.id,
                    "debit": 0,
                    "credit": 4,
                },
            ],
        )

    def test_stock_valuation_revaluation_avco_rounding_2_digits(self):
        product = self.product_avco
        self.env["decimal.precision"].search(
            [
                ("name", "=", "Product Price"),
            ]
        ).digits = 2

        self._make_in_move(product, 10000, 0.022)

        self.assertEqual(product.standard_price, 0.022)
        self.assertEqual(product.qty_available, 10000)
        self.assertEqual(product.total_value, 220)

        with freeze_time(Datetime.now() + timedelta(seconds=1)):
            product.write({"standard_price": 0.053})

        self.assertEqual(product.standard_price, 0.053)
        self.assertEqual(product.qty_available, 10000)
        self.assertEqual(product.total_value, 500)

    def test_stock_valuation_revaluation_avco_rounding_5_digits(self):
        product = self.product_avco

        self.env["decimal.precision"].search(
            [
                ("name", "=", "Product Price"),
            ]
        ).digits = 5
        self.env.company.currency_id.rounding = 0.00001

        with freeze_time(Datetime.now() - timedelta(seconds=1)):
            product.write({"standard_price": 0.00875})
        move1 = self._make_in_move(product, 10000)

        self.assertEqual(product.standard_price, 0.00875)
        self.assertEqual(product.qty_available, 10000)

        self.assertEqual(product.total_value, 87.5)

        with freeze_time(Datetime.now() + timedelta(seconds=1)):
            product.standard_price = 0.00975

        self.assertEqual(product.standard_price, 0.00975)
        self.assertEqual(product.qty_available, 10000)

        self.assertEqual(move1.value, 87.5)
        product_value = self.env["product.value"].search(
            [("product_id", "=", product.id)],
            order="create_date desc, id desc",
            limit=1,
        )
        self.assertEqual(product_value.value, 0.00975)

    def test_stock_valuation_revaluation_fifo(self):
        product = self.product_fifo

        move1 = self._make_in_move(product, 10, unit_cost=2)
        move2 = self._make_in_move(product, 10, unit_cost=4)

        self.assertEqual(product.standard_price, 3)
        self.assertEqual(product.qty_available, 20)

        self.assertEqual(product.total_value, 60)
        self.assertEqual(move1.remaining_value, 20)
        self.assertEqual(move2.remaining_value, 40)

        move2.value_manual = 60
        self.assertEqual(product.standard_price, 4)
        self.assertEqual(move1.remaining_value, 20)
        self.assertEqual(move2.remaining_value, 60)

        self._make_out_move(product, 10)
        self.assertEqual(move1.remaining_value, 0)
        self.assertEqual(move2.remaining_value, 60)
        self.assertEqual(product.standard_price, 6)

        self._make_out_move(product, 10)
        self.assertEqual(move1.remaining_value, 0)
        self.assertEqual(move2.remaining_value, 0)
        self.assertEqual(product.standard_price, 6)

    def test_stock_move_value_with_different_uom(self):
        move = self._make_in_move(
            self.product_standard, 1, uom_id=self.env.ref("uom.product_uom_dozen").id
        )
        self.assertEqual(
            move.value,
            120,
            "The move value should match the price in the correct UoM (12 * 10$).",
        )

    def test_product_valuation_scrap_different_uom(self):
        product = self.product_avco
        product.standard_price = 8
        uom_pack_6 = self.env.ref("uom.product_uom_pack_6")
        product.uom_ids = uom_pack_6
        self._make_in_move(product, 10)
        self.assertEqual(product.total_value, 80)
        self._make_out_move(product, 1, uom_id=uom_pack_6.id)
        self.assertEqual(product.total_value, 32)

    def test_journal_entry_created_with_given_accounting_date(self):
        product = self.product_standard_auto
        self._use_inventory_location_accounting()
        past_accounting_date = Date.today() - timedelta(days=7)
        inventory_quant = self.env["stock.quant"].create(
            {
                "location_id": self.stock_location.id,
                "product_id": product.id,
                "inventory_quantity": 10,
                "accounting_date": past_accounting_date,
            }
        )
        inventory_quant.action_apply_inventory()
        self.assertEqual(
            self._get_stock_valuation_move_lines().move_id.date, past_accounting_date
        )

    def test_journal_entry_with_packaging_uom_cogs(self):
        invoice = self._create_invoice(
            self.product_avco_auto,
            quantity=10,
            price_unit=100,
            product_uom_id=self.env.ref("uom.product_uom_pack_6"),
        )
        self.assertEqual(self.product_avco_auto.standard_price, 10)
        self.assertRecordValues(
            invoice.line_ids,
            [
                {
                    "account_id": self.category_avco_auto.property_account_income_categ_id.id,
                    "credit": 1000.0,
                    "debit": 0.0,
                },
                {
                    "account_id": self.account_receivable.id,
                    "credit": 0.0,
                    "debit": 1000.0,
                },
                {
                    "account_id": self.account_stock_valuation.id,
                    "credit": 600.0,
                    "debit": 0.0,
                },
                {"account_id": self.account_expense.id, "credit": 0.0, "debit": 600.0},
            ],
        )

    def test_inventory_user_can_validate_avco_picking(self):
        move = self.env["stock.move"].create(
            {
                "product_id": self.product_avco_auto.id,
                "product_uom_qty": 1,
                "product_uom_id": self.product_avco_auto.uom_id.id,
                "location_id": self.customer_location.id,
                "location_dest_id": self.stock_location.id,
            }
        )
        move._action_confirm()
        move.quantity = 1.0
        move.picked = True
        move.with_user(self.inventory_user)._action_done()
        self.assertEqual(move.state, "done")

    def test_product_value_details_computation_with_move_zero_quantity(self):
        move = self._make_in_move(self.product_avco, 0.0)
        self.assertEqual(move.quantity, 0.0)

        product_value = self.env["product.value"].create(
            {
                "move_id": move.id,
                "value": move.value_manual,
            }
        )
        product_value_form = Form(product_value)

        self.assertFalse(product_value_form.current_value_details)

    def test_average_cost_in_negative_quantity(self):
        self.product_avco.standard_price = 10

        self._make_out_move(self.product_avco, 10)
        self.assertEqual(self.product_avco.qty_available, -10)
        self.assertEqual(self.product_avco.standard_price, 10)

        self._make_in_move(self.product_avco, 5, unit_cost=15)
        self.assertEqual(self.product_avco.qty_available, -5)
        self.assertEqual(self.product_avco.standard_price, 15)

        self._make_in_move(self.product_avco, 5, unit_cost=20)
        self.assertEqual(self.product_avco.qty_available, 0)
        self.assertEqual(self.product_avco.standard_price, 20)

        self._make_out_move(self.product_avco, 5)
        self.assertEqual(self.product_avco.qty_available, -5)
        self.assertEqual(self.product_avco.standard_price, 20)

        self._make_in_move(self.product_avco, 10, unit_cost=25)
        self.assertEqual(self.product_avco.qty_available, 5)
        self.assertEqual(self.product_avco.standard_price, 25)

    def test_average_cost_dropship_in_negative_quantity(self):
        self.product_avco.standard_price = 10

        self._make_out_move(self.product_avco, 10)
        self.assertEqual(self.product_avco.qty_available, -10)
        self.assertEqual(self.product_avco.standard_price, 10)

        self._make_dropship_move(self.product_avco, 5, unit_cost=15)
        self.assertEqual(self.product_avco.qty_available, -10)
        self.assertEqual(self.product_avco.standard_price, 10)

        self._make_dropship_move(self.product_avco, 10, unit_cost=15)
        self.assertEqual(self.product_avco.qty_available, -10)
        self.assertEqual(self.product_avco.standard_price, 10)

        self._make_dropship_move(self.product_avco, 15, unit_cost=15)
        self.assertEqual(self.product_avco.qty_available, -10)
        self.assertEqual(self.product_avco.standard_price, 10)

    def test_avco_adjusted_valuation_updates_unit_cost_correctly(self):
        move = self._make_in_move(self.product_avco, 100, 10)
        self.assertEqual(move.quantity, 100.0)
        self.assertEqual(self.product_avco.total_value, 1000)
        self.assertEqual(self.product_avco.standard_price, 10)

        self.env["product.value"].create(
            {
                "product_id": self.product_avco.id,
                "move_id": move.id,
                "value": 2000,
            }
        )
        self.assertEqual(self.product_avco.total_value, 2000)
        self.assertEqual(self.product_avco.standard_price, 20)

    def test_avco_report_multiple_page(self):
        prod_avco = self.env["product.product"].create(
            {
                "standard_price": 10.0,
                "list_price": 20.0,
                "uom_id": self.uom.id,
                "is_storable": True,
                "name": "Avco Product",
                "categ_id": self.category_avco.id,
            }
        )
        recs = (
            self.env["stock.avco.report"]
            .search([("product_id", "=", prod_avco.id)])
            .sorted("date, id")
        )
        self.assertEqual(len(recs), 1)
        self._make_in_move(prod_avco, 1, 10)
        self._make_in_move(prod_avco, 1, 10)
        self._make_in_move(prod_avco, 1, 10)
        recs = (
            self.env["stock.avco.report"]
            .search([("product_id", "=", prod_avco.id)])
            .sorted("date, id")
        )
        self.assertEqual(len(recs), 4)
        recs[-2:]._compute_cumulative_fields()
        self.assertEqual(recs[-1].total_quantity, 3)
        self.assertEqual(recs[-1].total_value, 30)

    def test_update_standard_price_with_limited_access_users(self):
        product = self.product_fifo
        product.standard_price = 1.0

        location_b = self.env["stock.location"].create(
            {
                "name": "Location B",
                "usage": "internal",
                "location_id": self.stock_location.id,
            }
        )

        self.env["stock.quant"]._update_available_quantity(
            product, self.stock_location, 10.0
        )
        self.env["stock.quant"]._update_available_quantity(product, location_b, 100.0)

        self.assertEqual(product.total_value, 110)

        self.env["ir.access"].create(
            {
                "name": "Forbid Quant Access of Location B for Inventory Users",
                "model_id": self.env["ir.model"]._get_id("stock.quant"),
                "group_id": self.env.ref("stock.group_stock_user").id,
                "kind": "guard",
                "guard_scope": "members",
                "operation": "crud",
                "domain": f"[('location_id', '!=', {location_b.id})]",
            }
        )

        self.assertEqual(product.with_user(self.inventory_user).qty_available, 10)
        self.assertEqual(product.with_user(self.inventory_user).total_value, 110)

        self._make_out_move(product, 1, user=self.inventory_user)

        self.assertEqual(product.standard_price, 1.0)


class TestMoveValueAdjustmentAccess(TestStockValuationCommon):
    def test_non_manager_can_adjust_move_value(self):
        move = self._make_in_move(self.product_avco, 5, 10)
        pv_before = (
            self.env["product.value"].sudo().search_count([("move_id", "=", move.id)])
        )
        move.with_user(self.inventory_user).value_manual = 999.0
        pv_after = self.env["product.value"].sudo().search([("move_id", "=", move.id)])
        self.assertEqual(
            len(pv_after),
            pv_before + 1,
            "Adjusting a move's value as a non-manager must record a product.value row.",
        )
        self.assertEqual(pv_after.sorted("id")[-1].value, 999.0)


class TestProductPriceHistoryCreation(TestStockValuationCommon):
    def _price_rows(self, product):
        return (
            self.env["product.value"]
            .sudo()
            .search(
                [
                    ("product_id", "=", product.id),
                    ("move_id", "=", False),
                    ("lot_id", "=", False),
                ]
            )
        )

    def test_zero_price_product_creates_no_history(self):
        product = self.env["product.product"].create(
            {
                "name": "Zero Price",
                "is_storable": True,
                "categ_id": self.category_avco.id,
                "standard_price": 0.0,
            }
        )
        self.assertFalse(
            self._price_rows(product),
            "A product created at a 0 standard price must not record a price-history row.",
        )

    def test_nonzero_price_product_records_history(self):
        product = self.env["product.product"].create(
            {
                "name": "Priced",
                "is_storable": True,
                "categ_id": self.category_avco.id,
                "standard_price": 12.0,
            }
        )
        rows = self._price_rows(product)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.value, 12.0)
        self.assertIn("from 0 to 12.0", rows.description)
