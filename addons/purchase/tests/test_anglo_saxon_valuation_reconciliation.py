# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

import time

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestValuationReconciliation(ValuationReconciliationTestCase):

    def setUp(self):
        super(ValuationReconciliationTestCase, self).setUp()

        #set a price difference account on the category
        self.price_dif_account = self.env['account.account'].create({
            'name': 'Test price dif',
            'code': 'purchase_account_TEST_42',
            'user_type_id': self.env['account.account.type'].search([],limit=1).id,
            'reconcile': True,
            'company_id': self.company.id,
        })
        self.test_product_category.property_account_creditor_price_difference_categ = self.price_dif_account.id

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

    def receive_po(self, purchase_order):
        purchase_order.picking_ids.action_confirm()
        purchase_order.picking_ids.action_assign()
        for picking in purchase_order.picking_ids:
            for ml in picking.move_line_ids:
                ml.qty_done = ml.product_qty
        purchase_order.picking_ids.action_done()

    def test_shipment_invoice(self):
        """ Tests the case into which we receive the goods first, and then make the invoice.
        """
        test_product = self.test_product_delivery
        purchase_order = self.create_purchase(test_product)
        self.receive_po(purchase_order)

        invoice = self.create_invoice_for_po(purchase_order)
        self.currency_rate.rate = 7.76435463
        invoice.action_invoice_open()
        picking = self.env['stock.picking'].search([('purchase_id','=',purchase_order.id)])
        self.check_reconciliation(invoice, picking)

    def test_invoice_shipment(self):
        """ Tests the case into which we make the invoice first, and then receive the goods.
        """
        test_product = self.test_product_order
        purchase_order = self.create_purchase(test_product)

        invoice = self.create_invoice_for_po(purchase_order)
        invoice_line = self.env['account.invoice.line'].search([('invoice_id', '=', invoice.id)])
        invoice_line.quantity = 1

        self.currency_rate.rate = 13.834739702

        invoice.action_invoice_open()
        self.receive_po(purchase_order)
        picking = self.env['stock.picking'].search([('purchase_id','=',purchase_order.id)])
        self.check_reconciliation(invoice, picking)
