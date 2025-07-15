# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import Form, tagged
from odoo.exceptions import AccessError


@tagged('post_install', '-at_install')
class TestPurchaseInvoice(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a users
        group_purchase_user = cls.env.ref('purchase.group_purchase_user')
        group_employee = cls.env.ref('base.group_user')
        group_partner_manager = cls.env.ref('base.group_partner_manager')

        cls.purchase_user = cls.env['res.users'].with_context(
            no_reset_password=True
        ).create({
            'name': 'Purchase user',
            'login': 'purchaseUser',
            'email': 'pu@odoo.com',
            'group_ids': [(6, 0, [group_purchase_user.id, group_employee.id, group_partner_manager.id])],
        })

        cls.vendor = cls.env['res.partner'].create({
            'name': 'Supplier',
            'email': 'supplier.serv@supercompany.com',
        })

        cls.account_expense_product = cls.env['account.account'].create({
            'code': 'EXPENSE.PROD111',
            'name': 'Expense - Test Account',
            'account_type': 'expense',
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

        purchase_order.order_line.qty_received = 4
        purchase_order.action_create_invoice()
        invoice = purchase_order.invoice_ids
        with self.assertRaises(AccessError):
            invoice.action_post()

    def test_read_purchase_order(self):
        """ Check that a purchase user can read all purchase order and 'in' invoices"""
        purchase_user_2 = self.purchase_user.sudo().copy({
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
        purchase_order_user2.button_confirm()

        purchase_order_user2.order_line.qty_received = 4
        purchase_order_user2.action_create_invoice()
        vendor_bill_user2 = purchase_order_user2.invoice_ids

        # open purchase_order_user2 and vendor_bill_user2 with `self.purchase_user`
        purchase_order_user1 = Form(purchase_order_user2.with_user(self.purchase_user))
        purchase_order_user1 = purchase_order_user1.save()
        vendor_bill_user1 = Form(vendor_bill_user2.with_user(self.purchase_user))
        vendor_bill_user1 = vendor_bill_user1.save()

    def test_double_validation(self):
        """Only purchase managers can approve a purchase order when double
        validation is enabled"""
        group_purchase_manager = self.env.ref('purchase.group_purchase_manager')
        order = self.env['purchase.order'].create({
            "partner_id": self.vendor.id,
            "order_line": [
                (0, 0, {
                    'product_id': self.product.id,
                    'name': f'{self.product.name} {1:05}',
                    'price_unit': 79.80,
                    'product_qty': 15.0,
                }),
            ]})
        company = order.sudo().company_id
        company.po_double_validation = 'two_step'
        company.po_double_validation_amount = 0
        self.purchase_user.write({
            'company_ids': [(4, company.id)],
            'company_id': company.id,
            'group_ids': [(3, group_purchase_manager.id)],
        })
        order.with_user(self.purchase_user).button_confirm()
        self.assertEqual(order.state, 'to approve')
        order.with_user(self.purchase_user).button_approve()
        self.assertEqual(order.state, 'to approve')
        self.purchase_user.group_ids += group_purchase_manager
        order.with_user(self.purchase_user).button_approve()
        self.assertEqual(order.state, 'purchase')

    def test_create_product_purchase_user(self):
        uom = self.env.ref('uom.product_uom_gram')
        self.purchase_user.group_ids += self.env.ref('product.group_product_manager')
        product = self.env['product.template'].with_user(self.purchase_user).create({
            'name': 'Test Product UOM Default',
            'type': 'consu',
            'uom_id': uom.id,
        })
        self.assertTrue(product, "The default purchase UOM should be in the same category as the sale UOM.")
