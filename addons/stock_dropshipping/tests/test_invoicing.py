# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Author: Leonardo Pistone
# Copyright 2015 Camptocamp SA

from openerp.tests.common import TransactionCase


class TestCreateInvoice(TransactionCase):

    def setUp(self):
        super(TestCreateInvoice, self).setUp()
        self.Wizard = self.env['stock.invoice.onshipping']

        self.customer = self.env.ref('base.res_partner_3')
        product = self.env.ref('product.product_product_36')
        dropship_route = self.env.ref('stock_dropshipping.route_drop_shipping')

        # Create Sale Journal
        self.env['account.journal'].create({'name': 'Purchase Journal - Test', 'code': 'DSTPJ', 'type': 'purchase', 'company_id': self.env.ref('base.main_company').id})

        user_type_id = self.env.ref('account.data_account_type_payable')
        account_pay_id = self.env['account.account'].create({'code': 'X1012', 'name': 'Purchase - Test Payable Account', 'user_type': user_type_id.id, 'reconcile': True})
        user_type_id = self.env.ref('account.data_account_type_expenses')
        account_exp_id = self.env['account.account'].create({'code': 'X1013', 'name': 'Purchase - Test Expense Account', 'user_type': user_type_id.id, 'reconcile': True})

        self.customer.write({'property_account_payable': account_pay_id.id})

        product.product_tmpl_id.write({'property_account_expense': account_exp_id.id})

        self.so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
        })
        self.sol = self.env['sale.order.line'].create({
            'name': '/',
            'order_id': self.so.id,
            'product_id': product.id,
            'route_id': dropship_route.id,
        })

    def test_po_on_delivery_creates_correct_invoice(self):
        self.so.action_button_confirm()

        po = self.so.procurement_group_id.procurement_ids.purchase_id
        self.assertTrue(po)
        po.invoice_method = 'picking'
        po.signal_workflow('purchase_confirm')

        picking = po.picking_ids
        self.assertEqual(1, len(picking))
        picking.action_done()

        wizard = self.Wizard.with_context({
            'active_id': picking.id,
            'active_ids': [picking.id],
        }).create({})
        invoice_ids = wizard.create_invoice()
        invoices = self.env['account.invoice'].browse(invoice_ids)
        self.assertEqual(1, len(invoices))
        self.assertEqual(invoices.type, 'in_invoice')
        self.assertEqual(invoices, po.invoice_ids)
