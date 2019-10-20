# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCase
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestValuationReconciliation(ValuationReconciliationTestCase):

    def setUp(self):
        super(TestValuationReconciliation, self).setUp()
        self.account_receivable = self.env['account.account'].create({
            'code': 'X1111',
            'name': 'Sale - Test Receivable Account',
            'user_type_id': self.env.ref('account.data_account_type_receivable').id,
            'reconcile': True
        })

        self.account_income = self.env['account.account'].create({
            'code': 'X1112',
            'name': 'Sale - Test Account',
            'user_type_id': self.env.ref('account.data_account_type_direct_costs').id
        })

        self.env.ref('product.list0').currency_id = self.currency_two.id

        #set the invoice_policy to delivery to have an accurate COGS entry
        self.test_product_delivery.invoice_policy = "delivery"

    def _create_sale(self, product, date, quantity=1.0):
        rslt = self.env['sale.order'].create({
            'partner_id': self.test_partner.id,
            'currency_id': self.currency_two.id,
            'order_line': [
                (0, 0, {
                    'name': product.name,
                    'product_id': product.id,
                    'product_uom_qty': quantity,
                    'product_uom': product.uom_po_id.id,
                    'price_unit': self.product_price_unit,
                })],
            'date_order': date,
        })
        rslt.action_confirm()
        return rslt

    def _create_invoice_for_so(self, sale_order, product, date, quantity=1.0):
        rslt = self.env['account.move'].create({
            'partner_id': self.test_partner.id,
            'currency_id': self.currency_two.id,
            'type': 'out_invoice',
            'invoice_date': date,
            'invoice_line_ids': [(0, 0, {
                'name': 'test line',
                'account_id': self.account_income.id,
                'price_unit': self.product_price_unit,
                'quantity': quantity,
                'discount': 0.0,
                'product_uom_id': product.uom_id.id,
                'product_id': product.id,
                'sale_line_ids': [(6, 0, sale_order.order_line.ids)],
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

        sale_order = self._create_sale(test_product, '2108-01-01')
        self._process_pickings(sale_order.picking_ids)

        invoice = self._create_invoice_for_so(sale_order, test_product, '2018-02-12')
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_one.id,
            'company_id': self.company.id,
            'rate': 9.87366352,
            'name': '2018-02-01',
        })
        invoice.post()
        picking = self.env['stock.picking'].search([('sale_id', '=', sale_order.id)])
        self.check_reconciliation(invoice, picking, operation='sale')

    def test_invoice_shipment(self):
        """ Tests the case into which we make the invoice first, and then send
        the goods to our customer.
        """
        test_product = self.test_product_delivery
        #since the invoice come first, the COGS will use the standard price on product
        self.test_product_delivery.standard_price = 13
        self._set_initial_stock_for_product(test_product)

        sale_order = self._create_sale(test_product, '2018-01-01')

        invoice = self._create_invoice_for_so(sale_order, test_product, '2018-02-03')
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_one.id,
            'company_id': self.company.id,
            'rate': 0.974784,
            'name': '2018-02-01',
        })
        invoice.post()

        self._process_pickings(sale_order.picking_ids)

        picking = self.env['stock.picking'].search([('sale_id', '=', sale_order.id)])
        self.check_reconciliation(invoice, picking, operation='sale')

        #return the goods and refund the invoice
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_one.id,
            'company_id': self.company.id,
            'rate': 10.54739702,
            'name': '2018-03-01',
        })
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
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_one.id,
            'company_id': self.company.id,
            'rate': 9.56564564,
            'name': '2018-04-01',
        })
        refund_invoice_wiz = self.env['account.move.reversal'].with_context(active_model='account.move', active_ids=[invoice.id]).create({
            'reason': 'test_invoice_shipment_refund',
            'refund_method': 'cancel',
        })
        refund_invoice = self.env['account.move'].browse(refund_invoice_wiz.reverse_moves()['res_id'])
        self.assertTrue(
            invoice.invoice_payment_state == refund_invoice.invoice_payment_state == 'paid',
            "Invoice and refund should both be in 'Paid' state"
        )
        self.check_reconciliation(refund_invoice, return_pick, operation='sale')

    def test_multiple_shipments_invoices(self):
        """ Tests the case into which we deliver part of the goods first, then 2 invoices at different rates, and finally the remaining quantities
        """
        test_product = self.test_product_delivery
        self._set_initial_stock_for_product(test_product)

        sale_order = self._create_sale(test_product, '2018-01-01', quantity=5)

        self._process_pickings(sale_order.picking_ids, quantity=2.0)
        picking = self.env['stock.picking'].search([('sale_id', '=', sale_order.id)], order="id asc", limit=1)

        invoice = self._create_invoice_for_so(sale_order, test_product, '2018-02-03', quantity=3)
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_one.id,
            'company_id': self.company.id,
            'rate': 7.76435463,
            'name': '2018-02-01',
        })
        invoice.post()
        self.check_reconciliation(invoice, picking, full_reconcile=False, operation='sale')

        invoice2 = self._create_invoice_for_so(sale_order, test_product, '2018-03-12', quantity=2)
        self.env['res.currency.rate'].create({
            'currency_id': self.currency_one.id,
            'company_id': self.company.id,
            'rate': 13.834739702,
            'name': '2018-03-01',
        })
        invoice2.post()
        self.check_reconciliation(invoice2, picking, full_reconcile=False, operation='sale')

        self.env['res.currency.rate'].create({
            'currency_id': self.currency_one.id,
            'company_id': self.company.id,
            'rate': 12.195747002,
            'name': '2018-04-01',
        })
        self._process_pickings(sale_order.picking_ids.filtered(lambda x: x.state != 'done'), quantity=3.0)
        picking = self.env['stock.picking'].search([('sale_id', '=', sale_order.id)], order='id desc', limit=1)
        self.check_reconciliation(invoice2, picking, operation='sale')
