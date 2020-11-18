# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

import time

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCase
from odoo.tests.common import Form, tagged


@tagged('post_install', '-at_install')
class TestValuationReconciliation(ValuationReconciliationTestCase):

    def setUp(self):
        super(TestValuationReconciliation, self).setUp()

        #set a price difference account on the category
        self.price_dif_account = self.env['account.account'].create({
            'name': 'Test price dif',
            'code': 'purchase_account_TEST_42',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
            'reconcile': True,
            'company_id': self.company.id,
        })
        self.test_product_category.property_account_creditor_price_difference_categ = self.price_dif_account.id

    def _create_purchase(self, product, date, quantity=1.0, set_tax=False):
        rslt = self.env['purchase.order'].create({
            'partner_id': self.test_partner.id,
            'currency_id': self.currency_two.id,
            'order_line': [
                (0, 0, {
                    'name': product.name,
                    'product_id': product.id,
                    'product_qty': quantity,
                    'product_uom': product.uom_po_id.id,
                    'price_unit': self.product_price_unit,
                    'date_planned': date,
                    'taxes_id': [(6, 0, product.supplier_taxes_id.ids)] if set_tax else False,
                })],
             'date_order': date,
        })
        rslt.button_confirm()
        return rslt

    def _create_invoice_for_po(self, purchase_order, date):
        move_form = Form(self.env['account.move'].with_context(default_type='in_invoice'))
        move_form.invoice_date = date
        move_form.partner_id = self.test_partner
        move_form.currency_id = self.currency_two
        move_form.purchase_id = purchase_order
        return move_form.save()

    def test_shipment_invoice(self):
        """ Tests the case into which we receive the goods first, and then make the invoice.
        """
        test_product = self.test_product_delivery
        date_po_and_delivery = '2018-01-01'

        purchase_order = self._create_purchase(test_product, date_po_and_delivery)
        self._process_pickings(purchase_order.picking_ids, date=date_po_and_delivery)

        invoice = self._create_invoice_for_po(purchase_order, '2018-02-02')
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_one.id,
            'company_id': self.company.id,
            'rate': 7.76435463,
            'name': '2018-02-01',
        })
        invoice.post()
        picking = self.env['stock.picking'].search([('purchase_id','=',purchase_order.id)])
        self.check_reconciliation(invoice, picking)
        # cancel the invoice
        invoice.button_cancel()

    def test_invoice_shipment(self):
        """ Tests the case into which we make the invoice first, and then receive the goods.
        """
        # Create a PO and an invoice for it
        test_product = self.test_product_order
        purchase_order = self._create_purchase(test_product, '2017-12-01')

        invoice = self._create_invoice_for_po(purchase_order, '2017-12-23')
        move_form = Form(invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 1
        invoice = move_form.save()

        # The currency rate changes
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_one.id,
            'company_id': self.company.id,
            'rate': 13.834739702,
            'name': '2017-12-22',
        })

        # Validate the invoice and refund the goods
        invoice.post()
        self._process_pickings(purchase_order.picking_ids, date='2017-12-24')
        picking = self.env['stock.picking'].search([('purchase_id', '=', purchase_order.id)])
        self.check_reconciliation(invoice, picking)

        # The currency rate changes again
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_one.id,
            'company_id': self.company.id,
            'rate': 10.54739702,
            'name': '2018-01-01',
        })

        # Return the goods and refund the invoice
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking.ids, active_id=picking.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.action_assign()
        return_pick.move_lines.quantity_done = 1
        return_pick.action_done()
        self._change_pickings_date(return_pick, '2018-01-13')

        # The currency rate changes again
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_one.id,
            'company_id': self.company.id,
            'rate': 9.56564564,
            'name': '2018-03-12',
        })

        # Refund the invoice
        refund_invoice_wiz = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=[invoice.id]).create({
            'reason': 'test_invoice_shipment_refund',
            'refund_method': 'cancel',
            'date': '2018-03-15',
        })
        refund_invoice = self.env['account.move'].browse(refund_invoice_wiz.reverse_moves()['res_id'])

        # Check the result
        self.assertTrue(invoice.invoice_payment_state == refund_invoice.invoice_payment_state == 'paid'), "Invoice and refund should both be in 'Paid' state"
        self.check_reconciliation(refund_invoice, return_pick)

    def test_multiple_shipments_invoices(self):
        """ Tests the case into which we receive part of the goods first, then 2 invoices at different rates, and finally the remaining quantities
        """
        test_product = self.test_product_delivery
        date_po_and_delivery0 = '2017-01-01'
        purchase_order = self._create_purchase(test_product, date_po_and_delivery0, quantity=5.0)
        self._process_pickings(purchase_order.picking_ids, quantity=2.0, date=date_po_and_delivery0)
        picking = self.env['stock.picking'].search([('purchase_id', '=', purchase_order.id)], order="id asc", limit=1)

        invoice = self._create_invoice_for_po(purchase_order, '2017-01-15')
        move_form = Form(invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 3.0
        invoice = move_form.save()

        self.env['res.currency.rate'].create({
            'currency_id': self.currency_one.id,
            'company_id': self.company.id,
            'rate': 7.76435463,
            'name': '2017-02-01',
        })
        invoice.post()
        self.check_reconciliation(invoice, picking, full_reconcile=False)

        invoice2 = self._create_invoice_for_po(purchase_order, '2017-02-15')
        move_form = Form(invoice2)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 2.0
        invoice2 = move_form.save()

        self.env['res.currency.rate'].create({
            'currency_id': self.currency_one.id,
            'company_id': self.company.id,
            'rate': 13.834739702,
            'name': '2017-03-01',
        })
        invoice2.post()
        self.check_reconciliation(invoice2, picking, full_reconcile=False)

        self.env['res.currency.rate'].create({
            'currency_id': self.currency_one.id,
            'company_id': self.company.id,
            'rate': 12.195747002,
            'name': '2017-04-01',
        })
        # We don't need to make the date of processing explicit since the very last rate
        # will be taken
        self._process_pickings(purchase_order.picking_ids.filtered(lambda x: x.state != 'done'), quantity=3.0)
        picking = self.env['stock.picking'].search([('purchase_id', '=', purchase_order.id)], order='id desc', limit=1)
        self.check_reconciliation(invoice2, picking)

    def test_rounding_discount(self):
        self.env.ref("product.decimal_discount").digits = 5
        tax_exclude_id = self.env["account.tax"].create(
            {
                "name": "Exclude tax",
                "amount": "0.00",
                "type_tax_use": "purchase",
            }
        )

        test_product = self.test_product_delivery
        test_product.supplier_taxes_id = [(6, 0, tax_exclude_id.ids)]
        date_po_and_delivery = '2018-01-01'

        purchase_order = self._create_purchase(test_product, date_po_and_delivery, quantity=10000, set_tax=True)
        self._process_pickings(purchase_order.picking_ids, date=date_po_and_delivery)

        invoice = self._create_invoice_for_po(purchase_order, '2018-01-01')

        # Set a discount
        move_form = Form(invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.discount = 0.92431
        move_form.save()

        invoice.post()

        # Check the price difference amount.
        price_diff_line = invoice.line_ids.filtered(lambda l: l.account_id == self.price_dif_account)
        self.assertTrue(len(price_diff_line) == 1, "A price difference line should be created")
        self.assertAlmostEqual(price_diff_line.price_total, -6100.45)

        picking = self.env['stock.picking'].search([('purchase_id','=',purchase_order.id)])
        self.check_reconciliation(invoice, picking)

    def test_rounding_price_unit(self):
        self.env.ref("product.decimal_price").digits = 6

        test_product = self.test_product_delivery
        self.product_price_unit = 0.005
        date_po_and_delivery = '2018-01-01'

        purchase_order = self._create_purchase(test_product, date_po_and_delivery, quantity=100000)
        self._process_pickings(purchase_order.picking_ids, date=date_po_and_delivery)

        invoice = self._create_invoice_for_po(purchase_order, '2018-01-01')

        # Set a discount
        move_form = Form(invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 0.006
        move_form.save()

        invoice.post()

        # Check the price difference amount. It's expected that price_unit * qty != price_total.
        price_diff_line = invoice.line_ids.filtered(lambda l: l.account_id == self.price_dif_account)
        self.assertTrue(len(price_diff_line) == 1, "A price difference line should be created")
        self.assertAlmostEqual(price_diff_line.price_unit, 0.001)
        self.assertAlmostEqual(price_diff_line.price_total, 100.0)

        picking = self.env['stock.picking'].search([('purchase_id','=',purchase_order.id)])
        self.check_reconciliation(invoice, picking)
