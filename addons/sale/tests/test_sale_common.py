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
            'groups_id': [(6, 0, [group_manager.id, self.env.ref('base.group_user').id])]
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
        service_delivery = self.env['product.product'].create({
            'name': 'Cost-plus Contract',
            'categ_id': self.env.ref('product.product_category_5').id,
            'standard_price': 200.0,
            'list_price': 180.0,
            'type': 'service',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'uom_po_id': self.env.ref('uom.product_uom_unit').id,
            'default_code': 'SERV_DEL',
            'invoice_policy': 'delivery',
        })
        service_order_01 = self.env['product.product'].create({
            'name': 'Remodeling Service',
            'categ_id': self.env.ref('product.product_category_3').id,
            'standard_price': 40.0,
            'list_price': 90.0,
            'type': 'service',
            'uom_id': self.env.ref('uom.product_uom_hour').id,
            'uom_po_id': self.env.ref('uom.product_uom_hour').id,
            'description': 'Example of product to invoice on order',
            'default_code': 'PRE-PAID',
            'invoice_policy': 'order',
        })
        product_order_01 = self.env.ref('product.product_order_01')
        product_order_01.type = 'consu'
        self.products = OrderedDict([
            ('prod_order', product_order_01),
            ('serv_del', service_delivery),
            ('serv_order', service_order_01),
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
    def setUpClass(cls):
        super(TestCommonSaleNoChart, cls).setUpClass()

        # create a pricelist
        cls.pricelist_usd = cls.env['product.pricelist'].create({
            'name': 'USD pricelist',
            'active': True,
            'currency_id': cls.env.ref('base.USD').id,
            'company_id': cls.env.user.company_id.id,
        })

    @classmethod
    def setUpClassicProducts(cls):
        # Create an expense journal
        user_type_income = cls.env.ref('account.data_account_type_direct_costs')
        cls.account_income_product = cls.env['account.account'].create({
            'code': 'INCOME_PROD111',
            'name': 'Icome - Test Account',
            'user_type_id': user_type_income.id,
        })
        # Create category
        cls.product_category = cls.env['product.category'].create({
            'name': 'Product Category with Income account',
            'property_account_income_categ_id': cls.account_income_product.id
        })
        # Products
        uom_unit = cls.env.ref('uom.product_uom_unit')
        uom_hour = cls.env.ref('uom.product_uom_hour')
        cls.product_order = cls.env['product.product'].create({
            'name': "Zed+ Antivirus",
            'standard_price': 235.0,
            'list_price': 280.0,
            'type': 'consu',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'invoice_policy': 'order',
            'expense_policy': 'no',
            'default_code': 'PROD_ORDER',
            'service_type': 'manual',
            'taxes_id': False,
            'categ_id': cls.product_category.id,
        })
        cls.service_deliver = cls.env['product.product'].create({
            'name': "Cost-plus Contract",
            'standard_price': 200.0,
            'list_price': 180.0,
            'type': 'service',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'invoice_policy': 'delivery',
            'expense_policy': 'no',
            'default_code': 'SERV_DEL',
            'service_type': 'manual',
            'taxes_id': False,
            'categ_id': cls.product_category.id,
        })
        cls.service_order = cls.env['product.product'].create({
            'name': "Prepaid Consulting",
            'standard_price': 40.0,
            'list_price': 90.0,
            'type': 'service',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
            'invoice_policy': 'order',
            'expense_policy': 'no',
            'default_code': 'PRE-PAID',
            'service_type': 'manual',
            'taxes_id': False,
            'categ_id': cls.product_category.id,
        })
        cls.product_deliver = cls.env['product.product'].create({
            'name': "Switch, 24 ports",
            'standard_price': 55.0,
            'list_price': 70.0,
            'type': 'consu',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'invoice_policy': 'delivery',
            'expense_policy': 'no',
            'default_code': 'PROD_DEL',
            'service_type': 'manual',
            'taxes_id': False,
            'categ_id': cls.product_category.id,
        })

        cls.product_map = OrderedDict([
            ('prod_order', cls.product_order),
            ('serv_del', cls.service_deliver),
            ('serv_order', cls.service_order),
            ('prod_del', cls.product_deliver),
        ])

    @classmethod
    def setUpExpenseProducts(cls):
        # Create an expense journal
        user_type_expense = cls.env.ref('account.data_account_type_expenses')
        cls.account_expense_for_products = cls.env['account.account'].create({
            'code': 'EXP_PROD13',
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
