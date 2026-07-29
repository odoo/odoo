# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_account.tests.common import TestStockValuationCommon
from odoo.addons.sale_stock.tests.common import TestSaleStockCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestValuationReconciliationCommon(TestStockValuationCommon, TestSaleStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('EUR')
        cls.product_standard_auto.write({
            'standard_price': 42.0,
            'invoice_policy': 'delivery',
        })

    def test_shipment_invoice(self):
        """ Tests the case into which we send the goods to the customer before
        making the invoice
        """
        test_product = self.product_standard_auto
        self._make_in_move(test_product, 11, 13)

        sale_order = self._so_deliver(test_product, price=66.0, picking=False, partner=self.partner_b, date_order='2108-01-01')
        self._process_pickings(sale_order.picking_ids)

        self._create_invoice(test_product, price_unit=66.0, invoice_date='2018-02-12', account_id=self.account_income.id)

        amls = self.env['account.move.line'].search([('product_id', '=', test_product.id)])
        self.assertRecordValues(amls, [
            {'debit': 0.0, 'credit': 66.0, 'account_id': self.account_income.id},
            {'debit': 0.0, 'credit': 42.0, 'account_id': self.account_stock_valuation.id},
            {'debit': 42.0, 'credit': 0.0, 'account_id': self.account_expense.id},
        ])

    def test_invoice_shipment(self):
        """ Tests the case into which we make the invoice first, and then send
        the goods to our customer.
        """
        test_product = self.product_standard_auto
        # since the invoice come first, the COGS will use the standard price on product
        self.product_standard_auto.standard_price = 13
        self._make_in_move(test_product, 11, 13)

        sale_order = self._so_deliver(test_product, price=66.0, picking=False, partner=self.partner_b, date_order='2018-01-01')

        invoice = self._create_invoice(test_product, price_unit=66.0, invoice_date='2018-02-03', account_id=self.account_income.id)

        self._process_pickings(sale_order.picking_ids)

        amls = self.env['account.move.line'].search([('product_id', '=', test_product.id)])
        self.assertRecordValues(amls, [
            {'debit': 0.0, 'credit': 66.0, 'account_id': self.account_income.id},
            {'debit': 0.0, 'credit': 13.0, 'account_id': self.account_stock_valuation.id},
            {'debit': 13.0, 'credit': 0.0, 'account_id': self.account_expense.id},
        ])

        #return the goods and refund the invoice
        self._make_return(sale_order.picking_ids.move_ids, 1)
        new_invoice = self._refund(move_to_refund=invoice, post=False, is_modify=True)

        self.assertEqual(invoice.payment_state, 'reversed', "Invoice should be in 'reversed' state.")
        self.assertEqual(invoice.reversal_move_ids.payment_state, 'paid', "Refund should be in 'paid' state.")
        self.assertEqual(new_invoice.state, 'draft', "New invoice should be in 'draft' state.")

    def test_multiple_shipments_invoices(self):
        """ Tests the case into which we deliver part of the goods first, then 2 invoices at different rates, and finally the remaining quantities
        """
        test_product = self.product_standard_auto
        self._make_in_move(test_product, 11, 13)

        sale_order = self._so_deliver(test_product, quantity=5, price=66.0, picking=False, partner=self.partner_b, date_order='2018-01-01')

        self._process_pickings(sale_order.picking_ids, quantity=2.0)

        self._create_invoice(test_product, quantity=3, price_unit=66.0, invoice_date='2018-02-03', account_id=self.account_income.id)
        self._create_invoice(test_product, quantity=2, price_unit=66.0, invoice_date='2018-03-12', account_id=self.account_income.id)

        self._process_pickings(sale_order.picking_ids.filtered(lambda x: x.state != 'done'), quantity=3.0)

        # Final check, everything should be reconciled
        amls = self.env['account.move.line'].search([('product_id', '=', test_product.id)])
        self.assertRecordValues(amls, [
            {'debit': 0.0, 'credit': 132.0, 'account_id': self.account_income.id},
            {'debit': 0.0, 'credit': 84.0, 'account_id': self.account_stock_valuation.id},
            {'debit': 84.0, 'credit': 0.0, 'account_id': self.account_expense.id},
            {'debit': 0.0, 'credit': 198.0, 'account_id': self.account_income.id},
            {'debit': 0.0, 'credit': 126.0, 'account_id': self.account_stock_valuation.id},
            {'debit': 126.0, 'credit': 0.0, 'account_id': self.account_expense.id},
        ])

    def test_fifo_multiple_products(self):
        """ Test Automatic Inventory Valuation with FIFO costs method, 3 products,
            2,3,4 out svls and 2 in moves by product. This tests a more complex use case with anglo-saxon accounting.
        """
        product_1 = self.product_fifo_auto
        product_1.list_price = 10

        # product_2 similar to product_1 but with different output account
        product_2 = product_1.copy({'name': 'P2', 'standard_price': 20, 'list_price': 20})
        categ_2 = product_1.categ_id.copy()
        account_2 = self.env['account.account'].create({
            'name': 'Stock Valuation 2',
            'code': '100105',
            'account_type': 'asset_current',
        })
        categ_2.property_stock_valuation_account_id = account_2
        product_2.categ_id = categ_2

        # Create out_svls
        so = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_b.id,
            'currency_id': self.other_currency.id,
            'order_line': [
                (0, 0, {
                    'name': product.name,
                    'product_id': product.id,
                    'product_uom_qty': 2,
                    'product_uom_id': product.uom_id.id,
                    'price_unit': 10.0,
                }) for product in 2 * [product_1] + [product_2]],
            'date_order': '2021-01-01',
        })
        so.action_confirm()

        self._process_pickings(so.picking_ids)
        self.assertEqual(so.picking_ids.state, 'done')

        inv = self.env['account.move'].create({
            'partner_id': self.partner_b.id,
            'currency_id': self.other_currency.id,
            'move_type': 'out_invoice',
            'invoice_date': '2021-01-10',
            'invoice_line_ids': [(0, 0, {
                'name': 'test line',
                'account_id': self.account_income.id,
                'price_unit': 10.0,
                'quantity': 2,
                'discount': 0.0,
                'product_id': line.product_id.id,
                'sale_line_ids': [(6, 0, line.ids)],
            }) for line in so.order_line],
        })

        so.invoice_ids += inv
        inv.action_post()

        # Create in_moves for P1/P2
        for product in (product_1, product_2):
            self._make_in_move(product, 2, product.standard_price + 1)

        amls = self.env['account.move.line'].search([('product_id', 'in', [product_1.id, product_2.id])])
        self.assertRecordValues(amls, [
            {'debit': 0.0, 'credit': 10.0, 'account_id': self.account_income.id},
            {'debit': 0.0, 'credit': 10.0, 'account_id': self.account_income.id},
            {'debit': 0.0, 'credit': 10.0, 'account_id': self.account_income.id},
            {'debit': 0.0, 'credit': 20.0, 'account_id': self.account_stock_valuation.id},
            {'debit': 20.0, 'credit': 0.0, 'account_id': self.account_expense.id},
            {'debit': 0.0, 'credit': 20.0, 'account_id': self.account_stock_valuation.id},
            {'debit': 20.0, 'credit': 0.0, 'account_id': self.account_expense.id},
            {'debit': 0.0, 'credit': 40.0, 'account_id': account_2.id},
            {'debit': 40.0, 'credit': 0.0, 'account_id': self.account_expense.id},
        ])
