# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_account.tests.test_lot_valuation import TestLotValuation
from odoo.tests import tagged, Form
from odoo.fields import Command


@tagged('post_install', '-at_install')
class TestStockLandedCostsLots(TestLotValuation):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.productlc1 = cls.env['product.product'].create({
            'name': 'landed cost',
            'type': 'service',
            'landed_cost_ok': True,
            'categ_id': cls.env.ref('product.product_category_goods').id,
        })

    def _receive_in_lots(self, product, unit_cost, lot_qtys):
        """
        Receive product at a given unit cost through a purchase order.

        :param lot_qtys: list of (lot_name, quantity) tuples
        """
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_qty': sum(qty for _name, qty in lot_qtys),
                'price_unit': unit_cost,
                'tax_ids': [Command.clear()],
            })],
        })
        po.button_confirm()
        receipt = po.picking_ids
        receipt.move_ids.move_line_ids = [Command.clear()] + [Command.create({
            'product_id': product.id,
            'lot_name': lot_name,
            'quantity': qty,
            'location_id': receipt.location_id.id,
            'location_dest_id': receipt.location_dest_id.id,
        }) for lot_name, qty in lot_qtys]
        receipt.button_validate()
        return receipt

    def _apply_landed_cost(self, picking_ids, amount, product):
        lc_form = Form(self.env['stock.landed.cost'])
        for picking in picking_ids:
            lc_form.picking_ids.add(picking)
        with lc_form.cost_lines.new() as cost_line:
            cost_line.product_id = product
            cost_line.price_unit = amount
        lc = lc_form.save()
        lc.compute_landed_cost()
        lc.button_validate()
        return lc

    def test_stock_landed_costs_lots(self):
        """
        Check that a landed cost applied on receipts of lot-valuated products is spread
        equally across the receipts and, within a receipt, spread over its lots.
        """
        product_a, product_b = self.env['product.product'].create([{
            'name': 'product_a',
            'is_storable': True,
            'tracking': 'lot',
            'lot_valuated': True,
            'categ_id': self.category_avco_auto.id,
        }, {
            'name': 'product_b',
            'is_storable': True,
            'tracking': 'lot',
            'lot_valuated': True,
            'categ_id': self.category_avco_auto.id,
        }])
        receipt_a = self._receive_in_lots(product_a, 10, [('LClotA1', 5), ('LClotA2', 5), ('LClotA3', 5)])
        receipt_b = self._receive_in_lots(product_b, 11, [('LClotB1', 5), ('LClotB2', 5)])

        lc = self._apply_landed_cost(receipt_a | receipt_b, 6, self.productlc1)

        # Equal split across the two receipt moves: 6 / 2 = 3 per move
        self.assertRecordValues(lc.valuation_adjustment_lines, [
            {'additional_landed_cost': 3},
            {'additional_landed_cost': 3},
        ])

        self.assertEqual(lc.state, "done")
        self.assertRecordValues(lc.account_move_id.line_ids, [
            {'account_id': self.account_stock_valuation.id, 'debit': 3, 'credit': 0},
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 3},
            {'account_id': self.account_stock_valuation.id, 'debit': 3, 'credit': 0},
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 3},
        ])

        lots = self.env['stock.lot'].search([('name', 'ilike', 'LClot')])
        lot_a = lots.filtered(lambda l: l.product_id == product_a)
        lot_b = lots - lot_a
        # product_a: (15 * 10 + 3) / 15 = 10.2 ; product_b: (10 * 11 + 3) / 10 = 11.3
        self.assertRecordValues(lot_a, [
            {'standard_price': 10.2, 'total_value': 51},
            {'standard_price': 10.2, 'total_value': 51},
            {'standard_price': 10.2, 'total_value': 51},
        ])
        self.assertRecordValues(lot_b, [
            {'standard_price': 11.3, 'total_value': 56.5},
            {'standard_price': 11.3, 'total_value': 56.5},
        ])

        out_a = self._make_out_move(product_a, 9, lot_ids=[lot_a[0], lot_a[1], lot_a[2]])
        self.assertEqual(out_a.value, 91.8)  # 9 * 10.2
        self.assertRecordValues(lot_a, [
            {'product_qty': 2, 'total_value': 20.4},
            {'product_qty': 2, 'total_value': 20.4},
            {'product_qty': 2, 'total_value': 20.4},
        ])

        out_b = self._make_out_move(product_b, 4, lot_ids=[lot_b[0], lot_b[1]])
        self.assertEqual(out_b.value, 45.2)  # 4 * 11.3
        self.assertRecordValues(lot_b, [
            {'product_qty': 3, 'total_value': 33.9},
            {'product_qty': 3, 'total_value': 33.9},
        ])

    def test_landed_cost_when_partially_sold(self):
        """
        Check that the landed costs split correctly between lot/ serial numbers
        when some lot/serial number are empty (no share of the landed cost for those)
        or when some have a portion of their quantity already sold (check that it uses the
        remaining quantity)
        """
        product = self.env['product.product'].create({
            'name': 'product',
            'is_storable': True,
            'tracking': 'lot',
            'lot_valuated': True,
            'categ_id': self.category_fifo_auto.id,
        })
        # Receive 5 units split in 4 lots
        receipt = self._receive_in_lots(product, 10000, [('L1', 1), ('L2', 2), ('L3', 1), ('L4', 1)])
        lots = receipt.move_ids.move_line_ids.lot_id.sorted('id')
        # Deliver 2 Units, 1 from L1 and 1 form L2
        self._make_out_move(product, 2, lot_ids=[lots[0], lots[1]])

        # Add the landed cost after the delivery
        self._apply_landed_cost(receipt, 5000, self.productlc1)

        # The landed cost should add 5000 / 5 = 1000 per unit
        self.assertRecordValues(lots, [
            {'product_qty': 0, 'standard_price': 0, 'total_value': 0},
            {'product_qty': 1, 'standard_price': 11000, 'total_value': 11000},
            {'product_qty': 1, 'standard_price': 11000, 'total_value': 11000},
            {'product_qty': 1, 'standard_price': 11000, 'total_value': 11000},
        ])
