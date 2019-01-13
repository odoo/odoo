# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

import time

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestValuationReconciliation(ValuationReconciliationTestCase):

    def setUp(self):
        super(TestValuationReconciliation, self).setUp()

        #set a price difference account on the category
        self.price_dif_account = self.env['account.account'].create({
            'name': 'Test price dif',
            'code': 'purchase_account_TEST_42',
            'user_type_id': self.env['account.account.type'].search([],limit=1).id,
            'reconcile': True,
            'company_id': self.company.id,
        })
        self.test_product_category.property_account_creditor_price_difference_categ = self.price_dif_account.id

    def _create_purchase(self, product, date, quantity=1.0):
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
                })],
             'date_order': date,
        })
        rslt.button_confirm()
        return rslt

    def _create_invoice_for_po(self, purchase_order, date):
        account_receivable = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_receivable').id)], limit=1)
        rslt = self.env['account.invoice'].create({
            'purchase_id': purchase_order.id,
            'partner_id': self.test_partner.id,
            'currency_id': self.currency_two.id,
            'name': 'vendor bill',
            'type': 'in_invoice',
            'date_invoice': date,
            'date': date,
            'account_id': account_receivable.id,
        })
        rslt.purchase_order_change()
        return rslt

    def test_shipment_invoice(self):
        """ Tests the case into which we receive the goods first, and then make the invoice.
        """
        test_product = self.test_product_delivery
        purchase_order = self._create_purchase(test_product, '2018-01-01')
        self._process_pickings(purchase_order.picking_ids)

        invoice = self._create_invoice_for_po(purchase_order, '2018-02-02')
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_one.id,
            'company_id': self.company.id,
            'rate': 7.76435463,
            'name': '2018-02-01',
        })
        invoice.action_invoice_open()
        picking = self.env['stock.picking'].search([('purchase_id','=',purchase_order.id)])
        self.check_reconciliation(invoice, picking)
        # cancel the invoice
        invoice.journal_id.write({'update_posted': 1})
        invoice.action_cancel()

    def test_invoice_shipment(self):
        """ Tests the case into which we make the invoice first, and then receive the goods.
        """
        # Create a PO and an invoice for it
        test_product = self.test_product_order
        purchase_order = self._create_purchase(test_product, '2017-12-01')

        invoice = self._create_invoice_for_po(purchase_order, '2017-12-23')
        invoice_line = self.env['account.invoice.line'].search([('invoice_id', '=', invoice.id)])
        invoice_line.quantity = 1

        # The currency rate changes
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_one.id,
            'company_id': self.company.id,
            'rate': 13.834739702,
            'name': '2017-12-22',
        })

        # Validate the invoice and refund the goods
        invoice.action_invoice_open()
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
        stock_return_picking = self.env['stock.return.picking']\
            .with_context(active_ids=[picking.id], active_id=picking.id).create({})
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
        refund_invoice_wiz = self.env['account.invoice.refund'].with_context(active_ids=[invoice.id]).create({
            'description': 'test_invoice_shipment_refund',
            'filter_refund': 'cancel',
            'date': '2018-03-15',
            'date_invoice': '2018-03-15',
        })
        refund_invoice_wiz.invoice_refund()

        # Check the result
        refund_invoice = self.env['account.invoice'].search([('name', '=', 'test_invoice_shipment_refund')])[0]
        self.assertTrue(invoice.state == refund_invoice.state == 'paid'), "Invoice and refund should both be in 'Paid' state"
        self.check_reconciliation(refund_invoice, return_pick)

    def test_multiple_shipments_invoices(self):
        """ Tests the case into which we receive part of the goods first, then 2 invoices at different rates, and finally the remaining quantities
        """
        test_product = self.test_product_delivery
        purchase_order = self._create_purchase(test_product, '2017-01-01', quantity=5.0)
        self._process_pickings(purchase_order.picking_ids, quantity=2.0)
        picking = self.env['stock.picking'].search([('purchase_id', '=', purchase_order.id)], order="id asc", limit=1)

        invoice = self._create_invoice_for_po(purchase_order, '2017-01-15')
        invoice_line = self.env['account.invoice.line'].search([('invoice_id', '=', invoice.id)])
        invoice_line.quantity = 3
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_one.id,
            'company_id': self.company.id,
            'rate': 7.76435463,
            'name': '2017-02-01',
        })
        invoice.action_invoice_open()
        self.check_reconciliation(invoice, picking, full_reconcile=False)

        invoice2 = self._create_invoice_for_po(purchase_order, '2017-02-15')
        invoice_line = self.env['account.invoice.line'].search([('invoice_id', '=', invoice2.id)])
        invoice_line.quantity = 2
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_one.id,
            'company_id': self.company.id,
            'rate': 13.834739702,
            'name': '2017-03-01',
        })
        invoice2.action_invoice_open()
        self.check_reconciliation(invoice2, picking, full_reconcile=False)

        self.env['res.currency.rate'].create({
            'currency_id': self.currency_one.id,
            'company_id': self.company.id,
            'rate': 12.195747002,
            'name': '2017-04-01',
        })
        self._process_pickings(purchase_order.picking_ids.filtered(lambda x: x.state != 'done'), quantity=3.0)
        picking = self.env['stock.picking'].search([('purchase_id', '=', purchase_order.id)], order='id desc', limit=1)
        self.check_reconciliation(invoice2, picking)
