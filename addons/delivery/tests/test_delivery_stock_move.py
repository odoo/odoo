# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.tests import common


class StockMoveInvoice(common.TransactionCase):

    def setUp(self):
        super(StockMoveInvoice, self).setUp()
        self.ProductProduct = self.env['product.product']
        self.SaleOrder = self.env['sale.order']
        self.AccountJournal = self.env['account.journal']

        # self.company_id = self.env.ref('base.company')
        self.partner_18 = self.env.ref('base.res_partner_18')
        self.pricelist_id = self.env.ref('product.list0')
        self.product_11 = self.env.ref('product.product_product_11')
        self.product_uom_unit = self.env.ref('product.product_uom_unit')
        self.normal_delivery = self.env.ref('delivery.normal_delivery_carrier')

    def test_01_delivery_stock_move(self):
        # test that the store fields of stock moves are computed with invoice before delivery flow
        # set a weight on ipod 16GB
        self.product_11.write({
            'weight': 0.25,
            'weight_net': 0.2
        })

        self.sale_prepaid = self.SaleOrder.create({
            'partner_id': self.partner_18.id,
            'partner_invoice_id': self.partner_18.id,
            'partner_shipping_id': self.partner_18.id,
            'pricelist_id': self.pricelist_id.id,
            'order_policy': 'prepaid',
            'order_line': [(0, 0, {
                'name': 'Ipod',
                'product_id': self.product_11.id,
                'product_uom_qty': 2,
                'product_uos_qty': 2,
                'product_uom': self.product_uom_unit.id,
                'price_unit': 750.00,
            })],
            'carrier_id': self.normal_delivery.id
        })

        #I add delivery cost in Sale order.
        self.SaleOrder.browse(self.sale_prepaid.id).delivery_set()

        #I confirm the SO.
        self.sale_prepaid.signal_workflow('order_confirm')

        #I check that the invoice was created
        self.assertEqual(len(self.sale_prepaid.invoice_ids), 1, "Invoice not created.")

        # I confirm the invoice

        self.invoice = self.sale_prepaid.invoice_ids[0]
        self.invoice.signal_workflow('invoice_open')

        # I pay the invoice.
        self.invoice = self.sale_prepaid.invoice_ids[0]
        self.invoice.signal_workflow('invoice_open')

        self.journal = self.AccountJournal.search([('type', '=', 'cash'), ('company_id', '=', self.sale_prepaid.company_id.id)], limit=1)
        self.invoice.pay_and_reconcile(self.journal, self.invoice.amount_total)

        # Check the SO after paying the invoice
        self.assertNotEqual(self.sale_prepaid.invoice_count, 0, 'order not invoiced')
        self.assertTrue(self.sale_prepaid.invoiced, 'order is not paid')
        self.assertEqual(len(self.sale_prepaid.picking_ids), 1, 'pickings not generated')

        # check the stock moves

        move = self.sale_prepaid.picking_ids.move_lines
        self.assertEqual(move.product_qty, 2, 'wrong product_qty')
        self.assertEqual(move.weight, 0.5, 'wrong move weight')
        self.assertEqual(move.weight_net, 0.4, 'wrong move weight_net')

        # ship

        self.picking = self.sale_prepaid.picking_ids.action_done()

        # Check the SO after shipping

        self.assertEqual(self.sale_prepaid.state, 'done')
