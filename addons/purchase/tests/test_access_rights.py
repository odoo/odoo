# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.account_test_no_chart import TestAccountNoChartCommon
from odoo.exceptions import AccessError
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestPurchaseInvoice(TestAccountNoChartCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a users
        group_purchase_user = cls.env.ref('purchase.group_purchase_user')
        group_employee = cls.env.ref('base.group_user')

        cls.purchase_user = cls.env['res.users'].with_context(
            no_reset_password=True
        ).create({
            'name': 'Purchase user',
            'login': 'purchaseUser',
            'email': 'pu@odoo.com',
            'groups_id': [(6, 0, [group_purchase_user.id, group_employee.id])],
            'property_account_payable_id': cls.account_payable.id,
            'property_account_receivable_id': cls.account_receivable.id,
        })

        cls.vendor = cls.env['res.partner'].create({
            'name': 'Supplier',
            'email': 'supplier.serv@supercompany.com',
        })

        user_type_expense = cls.env.ref('account.data_account_type_expenses')
        cls.account_expense_product = cls.env['account.account'].create({
            'code': 'EXPENSE_PROD111',
            'name': 'Expense - Test Account',
            'user_type_id': user_type_expense.id,
        })
        # Create category
        cls.product_category = cls.env['product.category'].create({
            'name': 'Product Category with Expense account',
            'property_account_expense_categ_id': cls.account_expense_product.id
        })
        cls.product = cls.env['product.product'].create({
            'name': "Product",
            'standard_price': 200.0,
            'list_price': 180.0,
            'type': 'service',
        })

        cls.setUpAdditionalAccounts()
        cls.setUpAccountJournal()

    def test_create_purchase_order(self):
        """Check a purchase user can create a vendor bill from a purchase order but not post it"""
        purchase_order_form = Form(self.env['purchase.order'].with_user(self.purchase_user))
        purchase_order_form.partner_id = self.vendor
        with purchase_order_form.order_line.new() as line:
            line.name = self.product.name
            line.product_id = self.product
            line.product_qty = 4
            line.price_unit = 5

        purchase_order = purchase_order_form.save()
        purchase_order.button_confirm()

        action = purchase_order.with_user(self.purchase_user).action_view_invoice()
        invoice_form = Form(self.env['account.move'].with_user(self.purchase_user).with_context(
            action['context']
        ))
        invoice = invoice_form.save()
        with self.assertRaises(AccessError):
            invoice.post()

    def test_read_purchase_order(self):
        """ Check that a purchase user can read all purchase order and 'in' invoices"""
        purchase_user_2 = self.purchase_user.copy({
            'name': 'Purchase user 2',
            'login': 'purchaseUser2',
            'email': 'pu2@odoo.com',
        })

        purchase_order_form = Form(self.env['purchase.order'].with_user(purchase_user_2))
        purchase_order_form.partner_id = self.vendor
        with purchase_order_form.order_line.new() as line:
            line.name = self.product.name
            line.product_id = self.product
            line.product_qty = 4
            line.price_unit = 5

        purchase_order_user2 = purchase_order_form.save()
        action = purchase_order_user2.with_user(purchase_user_2).action_view_invoice()
        invoice_form = Form(self.env['account.move'].with_user(purchase_user_2).with_context(action['context']))
        vendor_bill_user2 = invoice_form.save()

        # open purchase_order_user2 and vendor_bill_user2 with `self.purchase_user`
        purchase_order_user1 = Form(purchase_order_user2.with_user(self.purchase_user))
        purchase_order_user1 = purchase_order_user1.save()
        vendor_bill_user1 = Form(vendor_bill_user2.with_user(self.purchase_user))
        vendor_bill_user1 = vendor_bill_user1.save()

    def test_read_purchase_order_2(self):
        """ Check that a 2 purchase users with open the vendor bill the same
        way even with a 'own documents only' record rule. """

        # edit the account.move record rule for purchase user in order to ensure
        # a user can only see his own invoices
        rule = self.env.ref('purchase.purchase_user_account_move_rule')
        rule.domain_force = "['&', ('type', 'in', ('in_invoice', 'in_refund', 'in_receipt')), ('invoice_user_id', '=', user.id)]"

        # create a purchase and make a vendor bill from it as purchase user 2
        purchase_user_2 = self.purchase_user.copy({
            'name': 'Purchase user 2',
            'login': 'purchaseUser2',
            'email': 'pu2@odoo.com',
        })

        purchase_order_form = Form(self.env['purchase.order'].with_user(purchase_user_2))
        purchase_order_form.partner_id = self.vendor
        with purchase_order_form.order_line.new() as line:
            line.name = self.product.name
            line.product_id = self.product
            line.product_qty = 4
            line.price_unit = 5

        purchase_order_user2 = purchase_order_form.save()
        action = purchase_order_user2.with_user(purchase_user_2).action_view_invoice()
        invoice_form = Form(self.env['account.move'].with_user(purchase_user_2).with_context(action['context']))
        vendor_bill_user2 = invoice_form.save()

        # check user 1 cannot read the invoice
        with self.assertRaises(AccessError):
            Form(vendor_bill_user2.with_user(self.purchase_user))

        # Check that calling 'action_view_invoice' return the same action despite the record rule
        action_user_1 = purchase_order_user2.with_user(self.purchase_user).action_view_invoice()
        purchase_order_user2.invalidate_cache()
        action_user_2 = purchase_order_user2.with_user(purchase_user_2).action_view_invoice()
        self.assertEqual(action_user_1, action_user_2)
