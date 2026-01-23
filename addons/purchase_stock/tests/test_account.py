from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form

from .common import PurchaseTestCommon


class TestPurchaseOrderInvoice(PurchaseTestCommon):
    def test_invoice_standard(self):
        po = self._create_purchase(self.product_standard, price_unit=12)
        self._receive(po)
        bill = self._create_bill(purchase_order=po)

        self.assertTrue(bill)
        self.assertEqual(po.order_line.qty_invoiced, 1)
        self.assertRecordValues(bill.line_ids, [
            {'account_id': self.account_expense.id, 'debit': 12.0, 'credit': 0.0},
            {'account_id': self.account_payable.id, 'debit': 0.0, 'credit': 12.0},
        ])
        closing = self._close()
        self.assertRecordValues(closing.line_ids, [
            {'account_id': self.account_stock_variation.id, 'debit': 0.0, 'credit': 10.0},
            {'account_id': self.account_stock_valuation.id, 'debit': 10.0, 'credit': 0.0},
        ])

    def test_invoice_standard_auto(self):
        po = self._create_purchase(self.product_standard_auto, price_unit=12)
        self._receive(po)
        bill = self._create_bill(purchase_order=po)

        self.assertTrue(bill)
        self.assertRecordValues(bill.line_ids, [
            {'account_id': self.account_stock_valuation.id, 'debit': 12.0, 'credit': 0.0},
            {'account_id': self.account_payable.id, 'debit': 0.0, 'credit': 12.0},
        ])
        closing = self._close()
        self.assertRecordValues(closing.line_ids, [
            {'account_id': self.account_stock_valuation.id, 'debit': 0.0, 'credit': 2.0},
            {'account_id': self.account_stock_variation.id, 'debit': 2.0, 'credit': 0.0},
        ])

    def test_invoice_standard_auto_with_pdiff(self):
        self._use_price_diff()
        po = self._create_purchase(self.product_standard_auto, price_unit=12)
        self._receive(po)
        bill = self._create_bill(purchase_order=po)

        self.assertTrue(bill)
        self.assertRecordValues(bill.line_ids, [
            {'account_id': self.account_stock_valuation.id, 'debit': 12.0, 'credit': 0.0},
            {'account_id': self.account_payable.id, 'debit': 0.0, 'credit': 12.0},
            {'account_id': self.account_price_diff.id, 'debit': 2.0, 'credit': 0.0},
            {'account_id': self.account_stock_valuation.id, 'debit': 0.0, 'credit': 2.0},
        ])
        with self.assertRaises(UserError):
            self._close()

    def test_invoice_standard_auto_with_pdiff_and_multi_currencies(self):
        self._use_price_diff()

        today = fields.Date.today()
        tomorrow = today + relativedelta(days=1)
        self._use_multi_currencies([
            (fields.Date.to_string(today), 2.0),
            (fields.Date.to_string(tomorrow), 4.0),
        ])

        po = self._create_purchase(self.product_standard_auto, quantity=10, price_unit=12, currency_id=self.other_currency.id)
        self._receive(po)
        with freeze_time(tomorrow):
            bill = self._create_bill(purchase_order=po)

        self.assertRecordValues(bill.line_ids, [
            {'account_id': self.account_stock_valuation.id, 'debit': 30.0, 'credit': 0.0},
            {'account_id': self.account_payable.id, 'debit': 0.0, 'credit': 30.0},
            {'account_id': self.account_price_diff.id, 'debit': 0.0, 'credit': 70.0},
            {'account_id': self.account_stock_valuation.id, 'debit': 70.0, 'credit': 0.0},
        ])

    def test_invoice_standard_auto_rounding_price_unit(self):
        self._use_price_diff()
        self.env.ref("product.decimal_price").digits = 6
        self.product_standard_auto.standard_price = 0.0005

        purchase_order = self._create_purchase(self.product_standard_auto, quantity=100000, receive=True)
        bill = self._create_bill(purchase_order=purchase_order, post=False)

        bill_form = Form(bill)
        with bill_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 0.0006
        bill_form.save()
        bill.action_post()
        self.assertEqual(purchase_order.picking_ids.move_ids.value, 60)
        self.assertRecordValues(bill.line_ids, [
            {'account_id': self.account_stock_valuation.id, 'debit': 60.0, 'credit': 0.0},
            {'account_id': self.account_payable.id, 'debit': 0.0, 'credit': 60.0},
            {'account_id': self.account_price_diff.id, 'debit': 10.0, 'credit': 0.0},
            {'account_id': self.account_stock_valuation.id, 'debit': 0.0, 'credit': 10.0},
        ])

    def test_invoice_standard_auto_with_discount(self):
        self._use_price_diff()
        self.product_standard_auto.standard_price = 100
        self.env.ref("product.decimal_discount").digits = 5

        purchase_order = self._create_purchase(self.product_standard_auto, price_unit=100, quantity=10000, receive=True)
        bill = self._create_bill(purchase_order=purchase_order, post=False)

        # Set a discount
        bill_form = Form(bill)
        with bill_form.invoice_line_ids.edit(0) as bill_line_form:
            bill_line_form.discount = 0.92431
        bill_form.save()
        bill.action_post()
        self.assertEqual(purchase_order.picking_ids.move_ids.value, 990756.9)
        self.assertRecordValues(bill.line_ids, [
            {'account_id': self.account_stock_valuation.id, 'debit': 990756.9, 'credit': 0.0},
            {'account_id': self.account_payable.id, 'debit': 0.0, 'credit': 990756.9},
            {'account_id': self.account_price_diff.id, 'debit': 0.0, 'credit': 9243.1},
            {'account_id': self.account_stock_valuation.id, 'debit': 9243.1, 'credit': 0.0},
        ])

    def test_invoice_avco(self):
        po = self._create_purchase(self.product_avco, price_unit=12)
        po_line = po.order_line
        self._receive(po)
        bill = self._create_bill(purchase_order=po)

        self.assertTrue(bill)
        self.assertEqual(po_line.qty_invoiced, 1)
        self.assertRecordValues(bill.line_ids, [
            {'account_id': self.account_expense.id, 'debit': 12.0, 'credit': 0.0},
            {'account_id': self.account_payable.id, 'debit': 0.0, 'credit': 12.0},
        ])
        closing = self._close()
        self.assertRecordValues(closing.line_ids, [
            {'account_id': self.account_stock_variation.id, 'debit': 0.0, 'credit': 12.0},
            {'account_id': self.account_stock_valuation.id, 'debit': 12.0, 'credit': 0.0},
        ])

    def test_invoice_avco_auto(self):
        po = self._create_purchase(self.product_avco_auto, price_unit=12)
        self._receive(po)
        bill = self._create_bill(purchase_order=po)

        self.assertTrue(bill)
        self.assertRecordValues(bill.line_ids, [
            {'account_id': self.account_stock_valuation.id, 'debit': 12.0, 'credit': 0.0},
            {'account_id': self.account_payable.id, 'debit': 0.0, 'credit': 12.0},
        ])
        with self.assertRaises(UserError):
            self._close()

    def test_invoice_avco_tax_without_account(self):
        tax_with_no_account = self.env['account.tax'].create({
            'name': "Tax with no account",
            'amount_type': 'fixed',
            'amount': 5,
            'sequence': 8,
        })
        po = self._create_purchase(self.product_avco_auto, 10, 10, tax_ids=[Command.set(tax_with_no_account.ids)])
        move = self._receive(po)
        self.assertEqual(move.value, 150)

        bill = self._create_bill(purchase_order=po)
        self.assertRecordValues(bill.line_ids, [
            {'account_id': self.account_stock_valuation.id, 'debit': 100.0, 'credit': 0.0},
            {'account_id': self.account_stock_valuation.id, 'debit': 50.0, 'credit': 0.0},
            {'account_id': self.account_payable.id, 'debit': 0.0, 'credit': 150.0},
        ])

    def test_invoice_fifo(self):
        po = self._create_purchase(self.product_fifo, price_unit=12)
        self._receive(po)
        bill = self._create_bill(purchase_order=po)

        self.assertTrue(bill)
        self.assertRecordValues(bill.line_ids, [
            {'account_id': self.account_expense.id, 'debit': 12.0, 'credit': 0.0},
            {'account_id': self.account_payable.id, 'debit': 0.0, 'credit': 12.0},
        ])
        closing = self._close()
        self.assertRecordValues(closing.line_ids, [
            {'account_id': self.account_stock_variation.id, 'debit': 0.0, 'credit': 12.0},
            {'account_id': self.account_stock_valuation.id, 'debit': 12.0, 'credit': 0.0},
        ])

    def test_invoice_fifo_auto(self):
        po = self._create_purchase(self.product_fifo_auto, price_unit=12)
        self._receive(po)
        bill = self._create_bill(purchase_order=po)

        self.assertTrue(bill)
        self.assertRecordValues(bill.line_ids, [
            {'account_id': self.account_stock_valuation.id, 'debit': 12.0, 'credit': 0.0},
            {'account_id': self.account_payable.id, 'debit': 0.0, 'credit': 12.0},
        ])

        with self.assertRaises(UserError):
            self._close()

    def test_invoice_refund(self):
        po = self._create_purchase(self.product_avco, price_unit=12)
        po_line = po.order_line
        self._receive(po)
        bill = self._create_bill(purchase_order=po)

        self.assertTrue(bill)
        self.assertEqual(po_line.qty_invoiced, 1)
        self.assertRecordValues(bill.line_ids, [
            {'account_id': self.account_expense.id, 'debit': 12.0, 'credit': 0.0},
            {'account_id': self.account_payable.id, 'debit': 0.0, 'credit': 12.0},
        ])
        closing = self._close()
        self.assertRecordValues(closing.line_ids, [
            {'account_id': self.account_stock_variation.id, 'debit': 0.0, 'credit': 12.0},
            {'account_id': self.account_stock_valuation.id, 'debit': 12.0, 'credit': 0.0},
        ])
        # Extra step to test refund
        refund = self._refund(bill)
        self.assertTrue(refund)
        self.assertRecordValues(refund.line_ids, [
            {'account_id': self.account_expense.id, 'debit': 0.0, 'credit': 12.0},
            {'account_id': self.account_payable.id, 'debit': 12.0, 'credit': 0.0},
        ])
        self.assertEqual(po_line.qty_invoiced, 0)
        self.assertEqual(self.product_avco.standard_price, 12.0)
        # Despite the refund, the inventory value should not be impacted
        with self.assertRaises(UserError):
            self._close()
        bill = self._create_bill(purchase_order=po, post=False)
        bill.invoice_line_ids.price_unit = 18
        bill.action_post()
        self.assertEqual(po_line.qty_invoiced, 1)
        closing = self._close()
        self.assertRecordValues(closing.line_ids, [
            {'account_id': self.account_stock_variation.id, 'debit': 0.0, 'credit': 6.0},
            {'account_id': self.account_stock_valuation.id, 'debit': 6.0, 'credit': 0.0},
        ])

    def test_invoice_refund_auto(self):
        po = self._create_purchase(self.product_fifo_auto, price_unit=12)
        po_line = po.order_line
        self._receive(po)
        bill = self._create_bill(purchase_order=po)

        self.assertTrue(bill)
        self.assertRecordValues(bill.line_ids, [
            {'account_id': self.account_stock_valuation.id, 'debit': 12.0, 'credit': 0.0},
            {'account_id': self.account_payable.id, 'debit': 0.0, 'credit': 12.0},
        ])

        with self.assertRaises(UserError):
            self._close()
        # Extra step to test refund
        refund = self._refund(bill)
        self.assertTrue(refund)
        self.assertRecordValues(refund.line_ids, [
            {'account_id': self.account_stock_valuation.id, 'debit': 0.0, 'credit': 12.0},
            {'account_id': self.account_payable.id, 'debit': 12.0, 'credit': 0.0},
        ])
        self.assertEqual(po_line.qty_invoiced, 0)
        self.assertEqual(self.product_fifo_auto.standard_price, 12.0)

        # Perpetual closing. Inventory account balance is zero so it will compensate with variation
        # (this entry should be compensated by an accrual later or another closing after the bill)
        closing_before_bill = self._close()
        self.assertTrue(closing_before_bill)
        self.assertRecordValues(closing_before_bill.line_ids, [
            {'account_id': self.account_stock_variation.id, 'debit': 0.0, 'credit': 12.0},
            {'account_id': self.account_stock_valuation.id, 'debit': 12.0, 'credit': 0.0},
        ])

        bill = self._create_bill(purchase_order=po, post=False)
        bill.invoice_line_ids.price_unit = 18
        bill.action_post()
        self.assertRecordValues(bill.line_ids, [
            {'account_id': self.account_stock_valuation.id, 'debit': 18.0, 'credit': 0.0},
            {'account_id': self.account_payable.id, 'debit': 0.0, 'credit': 18.0},
        ])
        self.assertEqual(po_line.qty_invoiced, 1)
        self.assertEqual(self.product_fifo_auto.standard_price, 18.0)

        # Should reverse the closing before bill
        closing_after_bill = self._close()
        self.assertTrue(closing_after_bill)
        self.assertRecordValues(closing_after_bill.line_ids, [
            {'account_id': self.account_stock_valuation.id, 'debit': 0.0, 'credit': 12.0},
            {'account_id': self.account_stock_variation.id, 'debit': 12.0, 'credit': 0.0},
        ])
