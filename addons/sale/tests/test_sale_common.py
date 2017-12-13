# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import OrderedDict
from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.addons.account.tests.account_test_no_chart import TestAccountNoChartCommon


class TestSale(AccountingTestCase):
    def setUp(self):
        super(TestSale, self).setUp()
        # some users
        group_manager = self.env.ref('sales_team.group_sale_manager')
        group_user = self.env.ref('sales_team.group_sale_salesman')
        self.manager = self.env['res.users'].create({
            'name': 'Andrew Manager',
            'login': 'manager',
            'email': 'a.m@example.com',
            'signature': '--\nAndreww',
            'notification_type': 'email',
            'groups_id': [(6, 0, [group_manager.id])]
        })
        self.user = self.env['res.users'].create({
            'name': 'Mark User',
            'login': 'user',
            'email': 'm.u@example.com',
            'signature': '--\nMark',
            'notification_type': 'email',
            'groups_id': [(6, 0, [group_user.id])]
        })
        # create quotation with differend kinds of products (all possible combinations)
        self.products = OrderedDict([
            ('prod_order', self.env.ref('product.product_order_01')),
            ('serv_del', self.env.ref('product.service_delivery')),
            ('serv_order', self.env.ref('product.service_order_01')),
            ('prod_del', self.env.ref('product.product_delivery_01')),
        ])

        self.partner = self.env.ref('base.res_partner_1')


class TestCommonSaleNoChart(TestAccountNoChartCommon):
    """ This class should be extended for test suite of sale flows with a minimal chart of accounting
        installed. This test suite should be executed at module installation.
        This class provides some method to generate testing data well configured, according to the minimal
        chart of account, defined in `TestAccountNoChartCommon` class.
    """

    @classmethod
    def setUpExpenseProducts(cls):
        # Create an expense journal
        user_type_expense = cls.env.ref('account.data_account_type_expenses')
        cls.account_expense_for_products = cls.env['account.account'].create({
            'code': 'NC1113',
            'name': 'Expense - Test Purchase Account',
            'user_type_id': user_type_expense.id
        })
        # Expense Products
        cls.product_ordered_cost = cls.env['product.product'].create({
            'name': "Ordered at cost",
            'standard_price': 8,
            'list_price': 10,
            'type': 'consu',
            'invoice_policy': 'order',
            'expense_policy': 'cost',
            'default_code': 'CONSU-ORDERED1',
            'service_type': 'manual',
            'taxes_id': False,
            'property_account_expense_id': cls.account_expense_for_products.id,
        })

        cls.product_deliver_cost = cls.env['product.product'].create({
            'name': "Delivered at cost",
            'standard_price': 8,
            'list_price': 10,
            'type': 'consu',
            'invoice_policy': 'delivery',
            'expense_policy': 'cost',
            'default_code': 'CONSU-DELI1',
            'service_type': 'manual',
            'taxes_id': False,
            'property_account_expense_id': cls.account_expense_for_products.id,
        })

        cls.product_order_sales_price = cls.env['product.product'].create({
            'name': "Ordered at sales price",
            'standard_price': 8,
            'list_price': 10,
            'type': 'consu',
            'invoice_policy': 'order',
            'expense_policy': 'sales_price',
            'default_code': 'CONSU-ORDERED2',
            'service_type': 'manual',
            'taxes_id': False,
            'property_account_expense_id': cls.account_expense_for_products.id,
        })

        cls.product_deliver_sales_price = cls.env['product.product'].create({
            'name': "Delivered at sales price",
            'standard_price': 8,
            'list_price': 10,
            'type': 'consu',
            'invoice_policy': 'delivery',
            'expense_policy': 'sales_price',
            'default_code': 'CONSU-DELI2',
            'service_type': 'manual',
            'taxes_id': False,
            'property_account_expense_id': cls.account_expense_for_products.id,
        })

        cls.product_no_expense = cls.env['product.product'].create({
            'name': "No expense",
            'standard_price': 8,
            'list_price': 10,
            'type': 'consu',
            'invoice_policy': 'delivery',
            'expense_policy': 'no',
            'default_code': 'CONSU-NO',
            'service_type': 'manual',
            'taxes_id': False,
            'property_account_expense_id': cls.account_expense_for_products.id,
        })
