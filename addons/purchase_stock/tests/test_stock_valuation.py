from dateutil.relativedelta import relativedelta
from freezegun.api import freeze_time

from odoo import Command, fields
from .common import PurchaseTestCommon


class TestPurchaseStockValuation(PurchaseTestCommon):
    def test_move_value(self):
        """This test ensure the move value is correct. The move value
        doesn't depend on the cost method. It represents the real price
        of the move base on its linked Bills and PO."""
        po = self._create_purchase(self.product, 5, 12)
        move_in_1 = self._receive(po, 2)
        self.assertEqual(move_in_1.value, 24)

        self._create_bill(purchase_order=po, quantity=2)
        self._create_bill(purchase_order=po, quantity=1, price_unit=8)
        self.assertAlmostEqual(move_in_1.value, 32 * 2 / 3, delta=0.01)

        move_in_2 = self._receive(po, 2)
        # bill 2 @ 12$ + bill 1 @ 8$ + po @ 12
        self.assertAlmostEqual(move_in_2.value, (32 * 1 / 3) + 12, delta=0.01)
        move_in_3 = self._receive(po, 1)
        # Value taken from PO since the 3 first units are billed
        self.assertAlmostEqual(move_in_3.value, 12, delta=0.01)
        self._create_bill(purchase_order=po, quantity=2, price_unit=15)
        value = 24 + 8 + 30
        self.assertAlmostEqual(move_in_1.value, value * 2 / 5, delta=0.01)
        self.assertAlmostEqual(move_in_2.value, value * 2 / 5, delta=0.01)
        self.assertAlmostEqual(move_in_3.value, value * 1 / 5, delta=0.01)

        self.assertEqual(po.order_line.qty_received, 5)
        self.assertEqual(po.order_line.qty_invoiced, 5)

    def test_move_value_credit_note(self):
        po = self._create_purchase(self.product_avco, 5, 10)
        move_in = self._receive(po)
        self.assertEqual(move_in.value, 50)

        bill = self._create_bill(purchase_order=po, price_unit=20)
        self.assertEqual(move_in.value, 100)

        self._refund(bill)
        self.assertEqual(move_in.value, 50)

        self._create_bill(purchase_order=po, price_unit=30)
        self.assertEqual(move_in.value, 150)

    def test_move_value_extra_quantity(self):
        po = self._create_purchase(self.product_avco, 5, 10)
        move_in = self._receive(po, 7)
        self.assertEqual(move_in.value, 70)

        self._create_bill(purchase_order=po, quantity=7, price_unit=20, post=True)
        self.assertEqual(move_in.value, 140)
        self.assertEqual(self.product_avco.total_value, 140)

    def test_move_value_at_date(self):
        self.env['product.value'].search([]).unlink()
        with freeze_time('2025-01-01'):
            po = self._create_purchase(self.product_avco, 10, 8)

        with freeze_time('2025-01-02'):
            self._receive(purchase_order=po)

        with freeze_time('2025-01-03'):
            self._create_bill(purchase_order=po, price_unit=12)

        self.assertEqual(self.product_avco.total_value, 120)
        self.assertEqual(self.product_avco.with_context(to_date="2025-01-01").total_value, 0)
        self.assertEqual(self.product_avco.with_context(to_date="2025-01-02").total_value, 80)
        self.assertEqual(self.product_avco.with_context(to_date="2025-01-03").total_value, 120)

    def test_move_value_with_small_decimals(self):
        self.env.ref('product.decimal_price').digits = 5
        po = self._create_purchase(self.product_avco, 1500, 3.30125)
        move = self._receive(purchase_order=po)
        self.assertEqual(move.value, 4951.88)

        self._create_bill(purchase_order=po)
        self.assertEqual(move.value, 4951.88)

    def test_move_value_multi_currency(self):
        self.env['product.value'].search([]).unlink()
        self._use_multi_currencies([
            ('2025-01-01', 1.25),
            ('2025-01-02', 1.5),
            ('2025-01-03', 1.75),
            ('2025-01-04', 2),
            ('2025-01-05', 3),
        ])
        with freeze_time('2025-01-01'):
            po = self._create_purchase(self.product_avco, 10, 10, currency_id=self.other_currency.id)

        with freeze_time('2025-01-02'):
            self._receive(purchase_order=po)

        with freeze_time('2025-01-04'):
            self._create_bill(purchase_order=po)

        self.assertEqual(self.product_avco.total_value, 50)
        self.assertEqual(self.product_avco.with_context(to_date="2025-01-01").total_value, 0)
        # It takes the rate from the delivery date (inverse of 1.5 = 0.666666667)
        self.assertEqual(self.product_avco.with_context(to_date="2025-01-02").total_value, 66.7)
        # Bill date rate
        self.assertEqual(self.product_avco.with_context(to_date="2025-01-04").total_value, 50)

    def test_move_value_multi_currency_bill_before_receipt(self):
        # rates = [
        #     ('today', 1.00),
        #     ('tomorrow, 2.00),
        #     ('day after tomorrow', 3.00),
        # ]
        self._use_multi_currencies()
        po = self._create_purchase(self.product_avco, 10, 10, currency_id=self.other_currency.id)
        self._create_bill(purchase_order=po, quantity=10)

        with freeze_time(fields.Date.today() + relativedelta(days=1)):
            self._receive(po)

        self.assertEqual(self.product_avco.total_value, 100)

    def test_move_value_uom(self):
        uom_pack_of_10 = self.env['uom.uom'].create({'name': 'Pack of 10', 'relative_uom_id': self.uom.id, 'relative_factor': 10})
        uom_pack_of_1_on_10 = self.env['uom.uom'].create({'name': 'Pack of 1/10', 'relative_uom_id': self.uom.id, 'relative_factor': 1 / 10})
        self.product_avco.uom_ids = [Command.link(uom_pack_of_10.id), Command.link(uom_pack_of_1_on_10.id)]
        po = self._create_purchase(self.product_avco, 5, 100, uom=uom_pack_of_10)
        move = self._receive(purchase_order=po)
        self.assertEqual(move.value, 500)
        self.assertEqual(self.product_avco.avg_cost, 10)

        bill = self._create_bill(purchase_order=po, post=False)
        bill.invoice_line_ids.product_uom_id = uom_pack_of_1_on_10
        bill.invoice_line_ids.quantity = 500
        bill.invoice_line_ids.price_unit = 1.2
        bill._post()
        self.assertEqual(move.value, 600)
        self.assertEqual(self.product_avco.avg_cost, 12)

    def test_move_value_after_po_update(self):
        po = self._create_purchase(self.product, 10, 10)
        move_in_1 = self._receive(po, 10)
        self.assertEqual(move_in_1.value, 100)

        po.order_line.price_unit = 15
        self.assertEqual(move_in_1.value, 150)

    def test_move_standard(self):
        po = self._create_purchase(self.product_standard, 5, 12)
        move_in_1 = self._receive(po, 2)
        self.assertEqual(self.product_standard.total_value, 20)

        self._create_bill(purchase_order=po, quantity=2)
        self.assertEqual(self.product_standard.total_value, 20)

        self._create_bill(purchase_order=po, quantity=1, price_unit=8)
        move_in_2 = self._receive(po, 2)
        # bill 2 @ 12$ + bill 1 @ 8$
        self.assertEqual(self.product_standard.total_value, 40)
        move_in_3 = self._receive(po, 1)
        self.assertEqual(self.product_standard.total_value, 50)
        self._create_bill(purchase_order=po, quantity=2, price_unit=15)
        self.assertEqual(self.product_standard.total_value, 50)
        self.assertEqual(self.product_standard.qty_available, 5)

        self.assertEqual(move_in_1.remaining_value, 20)
        self.assertEqual(move_in_2.remaining_value, 20)
        self.assertEqual(move_in_3.remaining_value, 10)

        # Check the standard price update, recompute everything
        self.product_standard.standard_price = 20
        self.assertEqual(self.product_standard.total_value, 100)
        self.assertEqual(self.product_standard.qty_available, 5)

        self.assertEqual(move_in_1.remaining_value, 40)
        self.assertEqual(move_in_2.remaining_value, 40)
        self.assertEqual(move_in_3.remaining_value, 20)

    def test_move_avco(self):
        po = self._create_purchase(self.product_avco, 5, 12)
        move_in_1 = self._receive(po, 2)
        self.assertEqual(self.product_avco.total_value, 24)

        self._create_bill(purchase_order=po, quantity=2)
        self.assertEqual(self.product_avco.total_value, 24)

        self._create_bill(purchase_order=po, quantity=1, price_unit=8)
        move_in_2 = self._receive(po, 2)
        # bill 2 @ 12$ + bill 1 @ 8$
        self.assertEqual(self.product_avco.total_value, 44)
        move_in_3 = self._receive(po, 1)
        self.assertEqual(self.product_avco.total_value, 56)
        self._create_bill(purchase_order=po, quantity=2, price_unit=15)
        self.assertEqual(self.product_avco.total_value, 62)
        self.assertEqual(self.product_avco.qty_available, 5)

        avg_cost = self.product_avco.avg_cost
        self.assertEqual(move_in_1.remaining_value, avg_cost * 2)
        self.assertEqual(move_in_2.remaining_value, avg_cost * 2)
        self.assertEqual(move_in_3.remaining_value, avg_cost)

    def test_move_fifo(self):
        """This test is similar to test_move_avco since all the move under
         a same purchase order share the value as an average flow. The FIFO
         only apply on different purchase orders.
         """
        po = self._create_purchase(self.product_fifo, 5, 12)
        move_in_1 = self._receive(po, 2)
        self.assertEqual(self.product_fifo.total_value, 24)

        self._create_bill(purchase_order=po, quantity=2)
        self.assertEqual(self.product_fifo.total_value, 24)

        self._create_bill(purchase_order=po, quantity=1, price_unit=8)
        move_in_2 = self._receive(po, 2)
        # bill 2 @ 12$ + bill 1 @ 8$
        self.assertEqual(self.product_fifo.total_value, 44)
        move_in_3 = self._receive(po, 1)
        self.assertEqual(self.product_fifo.total_value, 56)
        self._create_bill(purchase_order=po, quantity=2, price_unit=15)
        self.assertEqual(self.product_fifo.total_value, 62)
        self.assertEqual(self.product_fifo.qty_available, 5)

        avg_cost = self.product_fifo.avg_cost
        self.assertEqual(move_in_1.remaining_value, avg_cost * 2)
        self.assertEqual(move_in_2.remaining_value, avg_cost * 2)
        self.assertEqual(move_in_3.remaining_value, avg_cost)

    def test_move_fifo_2(self):
        po_1 = self._create_purchase(self.product_fifo, 1, 10, receive=True)
        po_2 = self._create_purchase(self.product_fifo, 1, 15, receive=True)
        po_3 = self._create_purchase(self.product_fifo, 1, 20, receive=True)
        self.assertEqual(self.product_fifo.total_value, 45)

        self._create_bill(purchase_order=po_1, price_unit=10)
        self._create_bill(purchase_order=po_2, price_unit=17)
        self._create_bill(purchase_order=po_3, price_unit=20)
        self.assertEqual(self.product_fifo.total_value, 47)

        self._make_out_move(self.product_fifo, 1)
        self.assertEqual(self.product_fifo.total_value, 37)
        self._make_out_move(self.product_fifo, 1)
        self.assertEqual(self.product_fifo.total_value, 20)
        self._make_out_move(self.product_fifo, 1)
        self.assertEqual(self.product_fifo.total_value, 0)
