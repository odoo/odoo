# -*- coding: utf-8 -*-

from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class StockMoveInvoice(AccountingTestCase):

    def setUp(self):
        super(StockMoveInvoice, self).setUp()
        self.ProductProduct = self.env['product.product']
        self.SaleOrder = self.env['sale.order']
        self.AccountJournal = self.env['account.journal']

        self.partner_18 = self.env.ref('base.res_partner_18')
        self.pricelist_id = self.env.ref('product.list0')
        self.product_11 = self.env.ref('product.product_product_11')
        self.product_cable_management_box = self.env.ref('stock.product_cable_management_box')
        self.product_uom_unit = self.env.ref('uom.product_uom_unit')
        self.normal_delivery = self.env.ref('delivery.normal_delivery_carrier')

    def test_01_delivery_stock_move(self):
        # Test if the stored fields of stock moves are computed with invoice before delivery flow
        self.product_11.write({
            'weight': 0.25,
        })

        self.sale_prepaid = self.SaleOrder.create({
            'partner_id': self.partner_18.id,
            'partner_invoice_id': self.partner_18.id,
            'partner_shipping_id': self.partner_18.id,
            'pricelist_id': self.pricelist_id.id,
            'order_line': [(0, 0, {
                'name': 'Cable Management Box',
                'product_id': self.product_cable_management_box.id,
                'product_uom_qty': 2,
                'product_uom': self.product_uom_unit.id,
                'price_unit': 750.00,
            })],
        })

        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': self.sale_prepaid.id,
            'default_carrier_id': self.normal_delivery.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()

        # I confirm the SO.
        self.sale_prepaid.action_confirm()
        self.sale_prepaid._create_invoices()

        # I check that the invoice was created
        self.assertEqual(len(self.sale_prepaid.invoice_ids), 1, "Invoice not created.")

        # I confirm the invoice

        self.invoice = self.sale_prepaid.invoice_ids
        self.invoice.post()

        # I pay the invoice.
        self.journal = self.AccountJournal.search([('type', '=', 'cash'), ('company_id', '=', self.sale_prepaid.company_id.id)], limit=1)

        register_payments = self.env['account.payment.register'].with_context(active_ids=self.invoice.ids).create({
            'journal_id': self.journal.id,
        })
        register_payments.create_payments()

        # Check the SO after paying the invoice
        self.assertNotEqual(self.sale_prepaid.invoice_count, 0, 'order not invoiced')
        self.assertTrue(self.sale_prepaid.invoice_status == 'invoiced', 'order is not invoiced')
        self.assertEqual(len(self.sale_prepaid.picking_ids), 1, 'pickings not generated')

        # Check the stock moves
        moves = self.sale_prepaid.picking_ids.move_lines
        self.assertEqual(moves[0].product_qty, 2, 'wrong product_qty')
        self.assertEqual(moves[0].weight, 2.0, 'wrong move weight')

        # Ship
        self.picking = self.sale_prepaid.picking_ids.action_done()
