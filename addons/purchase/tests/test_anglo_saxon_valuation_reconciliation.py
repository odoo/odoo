# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

import time

from odoo.tools import float_utils
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCase

import logging
_logger = logging.getLogger(__name__)

class TestValuationReconciliation(ValuationReconciliationTestCase):

    def _create_product_category(self): #overridden to set a price difference account
        self.price_dif_account = self.env['account.account'].create({
            'name': 'Test price dif',
            'code': 'purchase_account_TEST_42',
            'user_type_id': self.env['account.account.type'].search([],limit=1).id,
            'reconcile': True,
            'company_id': self.company.id,
        })

        return self.env['product.category'].create({
            'name': 'Test category',
            'property_valuation': 'real_time',
            'property_cost_method': 'fifo',
            'property_stock_valuation_account_id': self.valuation_account.id,
            'property_stock_account_input_categ_id': self.input_account.id,
            'property_stock_account_output_categ_id': self.output_account.id,
            'property_account_creditor_price_difference_categ': self.price_dif_account.id,
        })

    def create_purchase(self, product):
        rslt = self.env['purchase.order'].create({
            'partner_id': self.test_partner.id,
            'currency_id': self.currency_one.id,
            'order_line': [
                (0, 0, {
                    'name': product.name,
                    'product_id': product.id,
                    'product_qty': 1.0,
                    'product_uom': product.uom_po_id.id,
                    'price_unit': self.product_price_unit,
                    'date_planned': datetime.today(),
                })],
        })
        rslt.button_confirm()
        return rslt

    def create_invoice_for_po(self, purchase_order):
        account_receivable = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_receivable').id)], limit=1)
        rslt = self.env['account.invoice'].create({
            'purchase_id': purchase_order.id,
            'partner_id': self.test_partner.id,
            'reference_type': 'none',
            'currency_id': self.currency_two.id,
            'name': 'vendor bill',
            'type': 'in_invoice',
            'date_invoice': time.strftime('%Y') + '-12-22',
            'account_id': account_receivable.id,
        })
        rslt.purchase_order_change()
        return rslt

    def check_reconciliation(self, invoice, purchase_order, product):
        invoice_line = self.env['account.move.line'].search([('move_id','=',invoice.move_id.id), ('product_id','=', product.id), ('account_id','=',self.input_account.id)])
        self.assertEqual(len(invoice_line), 1, "Only one line should have been written by invoice in stock input account")
        self.assertNotEqual(float_utils.float_compare(invoice_line.amount_residual, invoice_line.debit, precision_digits=self.currency_one.decimal_places), 0, "The invoice's account move line should have been partly reconciled with stock valuation")

        valuation_line = self.env['stock.picking'].search([('purchase_id','=',purchase_order.id)]).move_lines.mapped('account_move_ids.line_ids').filtered(lambda x: x.account_id == self.input_account)
        self.assertEqual(len(valuation_line), 1, "Only one line should have been written for stock valuation in stock input account")
        self.assertTrue(valuation_line.reconciled or invoice_line.reconciled, "The valuation and invoice line should have been reconciled together.")

        self.assertEqual(float_utils.float_compare(invoice_line.debit - invoice_line.amount_residual,valuation_line.credit + valuation_line.amount_residual,self.currency_one.decimal_places), 0 , "The reconciled amount of invoice move line should match the stock valuation line.")

    def receive_po(self, purchase_order):
        purchase_order.picking_ids.action_confirm()
        purchase_order.picking_ids.action_assign()
        for picking in purchase_order.picking_ids:
            for ml in picking.move_line_ids:
                ml.qty_done = ml.product_qty
        purchase_order.picking_ids.action_done()

    def test_shipment_invoice(self):
        """ Tests the case into which we receive the goods first, and then
        make the invoice.
        """
        test_product = self.test_product_delivery
        purchase_order = self.create_purchase(test_product)
        self.receive_po(purchase_order)

        invoice = self.create_invoice_for_po(purchase_order)
        self.currency_rate.rate = 7.76435463
        invoice.action_invoice_open()
        self.check_reconciliation(invoice, purchase_order, test_product)

    def test_invoice_shipment(self):
        """ Tests the case into which we make the invoice first, and then receive
        the goods.
        """
        test_product = self.test_product_order
        purchase_order = self.create_purchase(test_product)

        invoice = self.create_invoice_for_po(purchase_order)
        invoice_line = self.env['account.invoice.line'].search([('invoice_id', '=', invoice.id)])
        invoice_line.quantity = 1

        self.currency_rate.rate = 13.834739702 # We test with a big change in the currency rate (which is pretty sound in a world where Trump rules the US)

        invoice.action_invoice_open()
        self.receive_po(purchase_order)
        self.check_reconciliation(invoice, purchase_order, test_product)