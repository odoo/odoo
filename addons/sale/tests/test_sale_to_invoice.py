# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tools import mute_logger
from .test_sale_common import TestCommonSaleNoChart


class TestSaleToInvoice(TestCommonSaleNoChart):

    @classmethod
    def setUpClass(cls):
        super(TestSaleToInvoice, cls).setUpClass()
        cls.setUpAdditionalAccounts()
        cls.setUpAccountJournal()

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.osv.orm')
    def setUp(self):
        super(TestSaleToInvoice, self).setUp()

    def test_sale_to_invoice(self):
        """ Testing for invoice create,validate and pay with invoicing and payment user."""
        # Usefull models
        IrModelData = self.env['ir.model.data']
        partner_obj = self.env['res.partner']
        journal_obj = self.env['account.journal']
        # Usefull record id
        group_id = IrModelData.xmlid_to_res_id('account.group_account_invoice') or False
        company_id = IrModelData.xmlid_to_res_id('base.main_company') or False

        # Usefull accounts
        account_recv_id = self.account_receivable
        account_rev_id = self.account_revenue

        # Add account to product
        product_template_id = self.env.ref('sale.advance_product_0').product_tmpl_id
        product_template_id.write({'property_account_income_id': account_rev_id})

        # In order to test, I create new user and applied Invoicing & Payments group.
        user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test@test.com',
            'company_id': 1,
            'groups_id': [(6, 0, [group_id])]})
        assert user, "User will not created."
        # I create partner for sales order.
        partner = partner_obj.create({
            'name': 'Test Customer',
            'email': 'testcustomer@test.com',
            'property_account_receivable_id': account_recv_id,
        })

        # In order to test I create sales order and confirmed it.
        order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'date_order': datetime.today(),
            'pricelist_id': self.env.ref('product.list0').id})
        assert order, "Sales order will not created."
        context = {"active_model": 'sale.order', "active_ids": [order.id], "active_id": order.id}
        order.with_context(context).action_confirm()
        # Now I create invoice.
        payment = self.env['sale.advance.payment.inv'].create({
            'advance_payment_method': 'fixed',
            'amount': 5,
            'product_id': self.env.ref('sale.advance_product_0').id,
        })
        invoice = payment.with_context(context).create_invoices()
        assert order.invoice_ids, "No any invoice is created for this sales order"
        # Now I validate pay invoice wihth Test User(invoicing and payment).
        for invoice in order.invoice_ids:
            invoice.with_context(context).invoice_validate()
