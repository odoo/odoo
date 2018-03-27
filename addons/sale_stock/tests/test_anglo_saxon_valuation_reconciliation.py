# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestValuationReconciliation(ValuationReconciliationTestCase):

    def _create_sale(self, product):
        rslt = self.env['sale.order'].create({
            'partner_id': self.test_partner.id,
            'currency_id': self.currency_two.id,
            'order_line': [
                (0, 0, {
                    'name': product.name,
                    'product_id': product.id,
                    'qty_to_invoice': 1.0,
                    'product_uom': product.uom_po_id.id,
                    'price_unit': self.product_price_unit,
                })],
        })
        rslt.action_confirm()
        return rslt

    def _create_invoice_for_so(self, sale_order, product):
        account_receivable = self.env['account.account'].create({'code': 'X1111', 'name': 'Sale - Test Receivable Account', 'user_type_id': self.env.ref('account.data_account_type_receivable').id, 'reconcile': True})
        account_income = self.env['account.account'].create({'code': 'X1112', 'name': 'Sale - Test Account', 'user_type_id': self.env.ref('account.data_account_type_direct_costs').id})
        rslt = self.env['account.invoice'].create({
            'partner_id': self.test_partner.id,
            'reference_type': 'none',
            'currency_id': self.currency_two.id,
            'name': 'customer invoice',
            'type': 'out_invoice',
            'date_invoice': time.strftime('%Y') + '-12-22',
            'account_id': account_receivable.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'test line',
                'origin': sale_order.name,
                'account_id': account_income.id,
                'price_unit': self.currency_one.compute(self.product_price_unit, self.currency_two, round=False),
                'quantity': 1.0,
                'discount': 0.0,
                'uom_id': product.uom_id.id,
                'product_id': product.id,
                'sale_line_ids': [(6, 0, [line.id for line in sale_order.order_line])],
            })],
        })

        sale_order.invoice_ids += rslt
        return rslt

    def _set_initial_stock_for_product(self, product):
        move1 = self.env['stock.move'].create({
            'name': 'Initial stock',
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.env.ref('stock.stock_location_stock').id,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'product_uom_qty': 11,
            'price_unit': 13,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.qty_done = 11
        move1._action_done()

    def test_shipment_invoice(self):
        """ Tests the case into which we send the goods to the customer before
        making the invoice
        """
        test_product = self.test_product_delivery
        self._set_initial_stock_for_product(test_product)

        sale_order = self._create_sale(test_product)
        self._process_pickings(sale_order.picking_ids)

        invoice = self._create_invoice_for_so(sale_order, test_product)
        self.currency_rate.rate = 9.87366352
        invoice.action_invoice_open()
        picking = self.env['stock.picking'].search([('sale_id', '=', sale_order.id)])
        self.check_reconciliation(invoice, picking)

    def test_invoice_shipment(self):
        """ Tests the case into which we make the invoice first, and then send
        the goods to our customer.
        """
        test_product = self.test_product_order
        self._set_initial_stock_for_product(test_product)

        sale_order = self._create_sale(test_product)

        invoice = self._create_invoice_for_so(sale_order, test_product)
        self.currency_rate.rate = 0.974784
        invoice.action_invoice_open()

        self._process_pickings(sale_order.picking_ids)

        picking = self.env['stock.picking'].search([('sale_id', '=', sale_order.id)])
        self.check_reconciliation(invoice, picking)

        #return the goods and refund the invoice
        self.currency_rate.rate = 10.54739702
        stock_return_picking = self.env['stock.return.picking']\
            .with_context(active_ids=[picking.id], active_id=picking.id).create({})
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.action_assign()
        return_pick.move_lines.quantity_done = 1
        return_pick.action_done()
        self.currency_rate.rate = 9.56564564
        refund_invoice_wiz = self.env['account.invoice.refund'].with_context(active_ids=[invoice.id]).create({
            'description': 'test_invoice_shipment_refund',
            'filter_refund': 'cancel',
        })
        refund_invoice_wiz.invoice_refund()
        refund_invoice = self.env['account.invoice'].search([('name', '=', 'test_invoice_shipment_refund')])[0]
        self.assertTrue(invoice.state == refund_invoice.state == 'paid'), "Invoice and refund should both be in 'Paid' state"
        self.check_reconciliation(refund_invoice, return_pick)
