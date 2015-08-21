# -*- coding: utf-8 -*-

from openerp.tests import common


class TestPurchase(common.TransactionCase):

    def test_purchase_to_invoice(self):
        """ Testing for invoice create,validate and pay with invoicing and payment user."""
        group_id = self.ref('account.group_account_invoice')
        product_id = self.ref('product.product_category_3')
        company_id = self.ref('base.main_company')
        location_id = self.ref('stock.stock_location_3')

        # Useful accounts
        user_type_id = self.ref('account.data_account_type_expenses')
        account_exp_id = self.env['account.account'].create({'code': 'X2020', 'name': 'Purchase - Test Expense Account', 'user_type_id': user_type_id, 'reconcile': True})
        user_type_id = self.ref('account.data_account_type_payable')
        account_pay_id = self.env['account.account'].create({'code': 'X1012', 'name': 'Purchase - Test Payable Account', 'user_type_id': user_type_id, 'reconcile': True})

        self.env['product.product'].browse(product_id).product_tmpl_id.write({'property_account_expense_id': account_exp_id})

        # Create Purchase Journal
        self.env['account.journal'].create({'name': 'Purchase Journal - Test', 'code': 'PTPJ', 'type': 'purchase'})

        # In order to test, I create new user and applied Invoicing & Payments group.
        user = self.env['res.users'].with_context({'no_reset_password': True}).create({
            'name': 'Test User',
            'login': 'test@test.com',
            'company_id': company_id,
            'groups_id': [(6, 0, [group_id])]})
        assert user, "User will not created."
        # I create partner for purchase order.
        partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'testcustomer@test.com',
            'property_account_payable_id': account_pay_id,
        })
        
        # In order to test I create purchase order and confirmed it.
        order = self.env['purchase.order'].create({
            'partner_id': partner.id,
            'location_id': location_id, })
        self.env['purchase.order.line'].create({
            'order_id': order.id,
            'product_id': product_id,
            'product_qty': 100.0,
            'product_uom': 1,
            'price_unit': 89.0,
            'name': 'Service',
            'date_planned': '2014-05-31'})
        assert order, "purchase order will not created."
        context = {"active_model": 'purchase.order', "active_ids": [order.id], "active_id": order.id}
        order.with_context(context).wkf_confirm_order()
        # In order to test I create invoice.
        invoice = order.with_context(context).action_invoice_create()
        assert invoice, "No any invoice is created for this purchase order"
        # In order to test I validate invoice wihth Test User(invoicing and payment).
        res = self.env['account.invoice'].browse(invoice).with_context(context).invoice_validate()
        self.assertTrue(res, 'Invoice will not validated')
