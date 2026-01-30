# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_account.tests.common import TestStockValuationCommon
from odoo.addons.sale_stock.tests.common import TestSaleStockCommon
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestValuationReconciliationCommon(TestStockValuationCommon, TestSaleStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('EUR')
        cls.product_standard_auto = cls.env['product.product'].create({
            'name': 'Test product template invoiced on delivery',
            'standard_price': 42.0,
            'is_storable': True,
            'categ_id': cls.category_standard_auto.id,
            'uom_id': cls.uom.id,
            'invoice_policy': 'delivery',
        })
        cls.product_standard_auto_2 = cls.env['product.product'].create({
            'name': 'Test product template invoiced on delivery 2',
            'standard_price': 42.0,
            'is_storable': True,
            'categ_id': cls.category_standard_auto.id,
            'uom_id': cls.uom.id,
            'invoice_policy': 'delivery',
        })

    def _process_pickings(self, pickings, quantity=None):
        for move in pickings.move_ids:
            move._action_assign()
            if quantity is not None:
                move.write({'quantity': quantity, 'picked': True})
            else:
                move.write({'quantity': move.product_uom_qty, 'picked': True})
        pickings.button_validate()

    def test_shipment_invoice(self):
        """ Tests the case into which we send the goods to the customer before
        making the invoice
        """
        test_product = self.product_standard_auto
        self._make_in_move(test_product, 11, 13)

        sale_order = self._so_deliver(test_product, quantity=1, price=66.0, picking=False, partner=self.partner_b, date_order='2108-01-01', currency=self.other_currency)
        self._process_pickings(sale_order.picking_ids)

        self._create_invoice(test_product, quantity=1, price_unit=66.0, invoice_date='2018-02-12', currency_id=self.other_currency.id, account_id=self.account_income.id)

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

        sale_order = self._so_deliver(test_product, quantity=1, price=66.0, picking=False, partner=self.partner_b, date_order='2018-01-01', currency=self.other_currency)

        invoice = self._create_invoice(test_product, quantity=1, price_unit=66.0, invoice_date='2018-02-03', currency_id=self.other_currency.id, account_id=self.account_income.id)

        self._process_pickings(sale_order.picking_ids)

        amls = self.env['account.move.line'].search([('product_id', '=', test_product.id)])
        self.assertRecordValues(amls, [
            {'debit': 0.0, 'credit': 66.0, 'account_id': self.account_income.id},
            {'debit': 0.0, 'credit': 13.0, 'account_id': self.account_stock_valuation.id},
            {'debit': 13.0, 'credit': 0.0, 'account_id': self.account_expense.id},
        ])

        #return the goods and refund the invoice
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=sale_order.picking_ids.ids, active_id=sale_order.picking_ids.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.action_create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.action_assign()
        return_pick.move_ids.write({'quantity': 1, 'picked': True})
        return_pick._action_done()
        refund_invoice_wiz = self.env['account.move.reversal'].with_context(active_model='account.move', active_ids=[invoice.id]).create({
            'reason': 'test_invoice_shipment_refund',
            'journal_id': invoice.journal_id.id,
        })
        new_invoice = self.env['account.move'].browse(refund_invoice_wiz.modify_moves()['res_id'])
        self.assertEqual(invoice.payment_state, 'reversed', "Invoice should be in 'reversed' state.")
        self.assertEqual(invoice.reversal_move_ids.payment_state, 'paid', "Refund should be in 'paid' state.")
        self.assertEqual(new_invoice.state, 'draft', "New invoice should be in 'draft' state.")

    def test_multiple_shipments_invoices(self):
        """ Tests the case into which we deliver part of the goods first, then 2 invoices at different rates, and finally the remaining quantities
        """
        test_product = self.product_standard_auto
        self._make_in_move(test_product, 11, 13)

        sale_order = self._so_deliver(test_product, quantity=5, price=66.0, picking=False, partner=self.partner_b, date_order='2018-01-01', currency=self.other_currency)

        self._process_pickings(sale_order.picking_ids, quantity=2.0)

        self._create_invoice(test_product, quantity=3, price_unit=66.0, invoice_date='2018-02-03', currency_id=self.other_currency.id, account_id=self.account_income.id)
        self._create_invoice(test_product, quantity=2, price_unit=66.0, invoice_date='2018-03-12', currency_id=self.other_currency.id, account_id=self.account_income.id)

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
        wh = self.warehouse
        stock_loc = wh.lot_stock_id
        in_type = wh.in_type_id

        product_1 = self.product_fifo_auto
        product_1.standard_price = 10
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
        in_moves = self.env['stock.move'].create([{
            'description_picking': '%s-%s' % (str(quantity), str(product)),
            'product_id': product.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': stock_loc.id,
            'product_uom': self.env.ref('uom.product_uom_unit').id,
            'product_uom_qty': quantity,
            'price_unit': product.standard_price + 1,
            'picking_type_id': in_type.id,
        } for product, quantity in zip(
            [product_1, product_2],
            [2.0, 2.0]
        )])
        in_moves._action_confirm()
        for move in in_moves:
            move.quantity = move.product_uom_qty
            move.picked = True
        in_moves._action_done()

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
