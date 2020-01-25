# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict
from odoo.addons.account.tests.common import AccountTestCommon
from odoo.addons.account.tests.common import AccountTestNoChartCommon, AccountTestNoChartCommonMultiCompany

class TestSaleCommon(AccountTestCommon):

    @classmethod
    def setUpClass(cls):
        super(TestSaleCommon, cls).setUpClass()
        # some users
        group_manager = cls.env.ref('sales_team.group_sale_manager')
        group_user = cls.env.ref('sales_team.group_sale_salesman')
        cls.manager = cls.env['res.users'].create({
            'name': 'Andrew Manager',
            'login': 'manager',
            'email': 'a.m@example.com',
            'signature': '--\nAndreww',
            'notification_type': 'email',
            'groups_id': [(6, 0, [group_manager.id, cls.env.ref('base.group_user').id])]
        })
        cls.user = cls.env['res.users'].create({
            'name': 'Mark User',
            'login': 'user',
            'email': 'm.u@example.com',
            'signature': '--\nMark',
            'notification_type': 'email',
            'groups_id': [(6, 0, [group_user.id])]
        })
        # create quotation with differend kinds of products (all possible combinations)
        service_delivery = cls.env['product.product'].create({
            'name': 'Cost-plus Contract',
            # 'categ_id': cls.env.ref('product.product_category_5').id,
            'categ_id': cls.env.ref('product.product_category_all').id,
            'standard_price': 200.0,
            'list_price': 180.0,
            'type': 'service',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'uom_po_id': cls.env.ref('uom.product_uom_unit').id,
            'default_code': 'SERV_DEL',
            'invoice_policy': 'delivery',
        })
        service_order_01 = cls.env['product.product'].create({
            'name': 'Remodeling Service',
            'categ_id': cls.env.ref('product.product_category_all').id,
            'standard_price': 40.0,
            'list_price': 90.0,
            'type': 'service',
            'uom_id': cls.env.ref('uom.product_uom_hour').id,
            'uom_po_id': cls.env.ref('uom.product_uom_hour').id,
            'description': 'Example of product to invoice on order',
            'default_code': 'PRE-PAID',
            'invoice_policy': 'order',
        })
        product_order_01 = cls.env['product.product'].create({
            'name': 'Office Design Software',
            'categ_id': cls.env.ref('product.product_category_all').id,
            'standard_price': 235.0,
            'list_price': 280.0,
            'type': 'consu', # Will be changed in 'product' in sale_stock
            'weight': 0.01,
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'uom_po_id': cls.env.ref('uom.product_uom_unit').id,
            'default_code': 'FURN_9999',
            'invoice_policy': 'order',
        })
        product_delivery_01 = cls.env['product.product'].create({
            'name': 'Office Chair',
            'categ_id': cls.env.ref('product.product_category_all').id,
            'standard_price': 55.0,
            'list_price': 70.0,
            'type': 'consu', # Will be changed in 'product' in sale_stock
            'weight': 0.01,
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'uom_po_id': cls.env.ref('uom.product_uom_unit').id,
            'default_code': 'FURN_7777',
            'invoice_policy': 'delivery',
        })
        cls.products = OrderedDict([
            ('prod_order', product_order_01),
            ('serv_del', service_delivery),
            ('serv_order', service_order_01),
            ('prod_del', product_delivery_01),
        ])

        cls.partner = cls.env['res.partner'].create({'name': 'A test Partner'})


class TestCommonSaleNoChart(AccountTestNoChartCommon):
    """ This class should be extended for test suite of sale flows with a minimal chart of accounting
        installed. This test suite should be executed at module installation.
        This class provides some method to generate testing data well configured, according to the minimal
        chart of account, defined in `AccountTestNoChartCommon` class.
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


class TestCommonSaleMultiCompanyNoChart(AccountTestNoChartCommonMultiCompany, TestCommonSaleNoChart):
    """ This class should be extended for test suite of sale flows with a minimal chart of accounting
        installed. This test suite should be executed at module installation.
        This class provides some method to generate testing data well configured, according to the minimal
        chart of account, defined in `TestAccountNoChartCommon` class.
    """

    @classmethod
    def setUpClass(cls):
        super(TestCommonSaleMultiCompanyNoChart, cls).setUpClass()
        cls.setUpAdditionalAccounts()

    @classmethod
    def setUpClassicProducts(cls):
        super(TestCommonSaleMultiCompanyNoChart, cls).setUpClassicProducts()
        # Create an expense journal
        user_type_income = cls.env.ref('account.data_account_type_direct_costs')
        cls.account_income_product_company_B = cls.env['account.account'].create({
            'code': 'INCOME_PROD111',
            'name': 'Income - Test Account Company B',
            'user_type_id': user_type_income.id,
            'company_id': cls.company_B.id,
        })
        # Create category
        cls.product_category_company_B = cls.env['product.category'].create({
            'name': 'Product Category with Income account Company B',
            'property_account_income_categ_id': cls.account_income_product_company_B.id
        })
        # Products
        uom_unit = cls.env.ref('uom.product_uom_unit')
        uom_hour = cls.env.ref('uom.product_uom_hour')

        cls.product_order_company_B = cls.env['product.product'].create({
            'name': "Pigeon pie",
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
            'categ_id': cls.product_category_company_B.id,
        })

        cls.service_deliver_company_B = cls.env['product.product'].create({
            'name': "Golden Company Contract",
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
            'categ_id': cls.product_category_company_B.id,
        })

        cls.service_order_company_B = cls.env['product.product'].create({
            'name': "Maester Consulting",
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
            'categ_id': cls.product_category_company_B.id,
        })

        cls.product_deliver_company_B = cls.env['product.product'].create({
            'name': "Swords",
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
            'categ_id': cls.product_category_company_B.id,
        })

    @classmethod
    def setUpExpenseProducts(cls):
        super(TestCommonSaleMultiCompanyNoChart, cls).setUpExpenseProducts()
        cls.product_ordered_cost_company_B = cls.env['product.product'].create({
            'name': "Ordered at cost",
            'standard_price': 8,
            'list_price': 10,
            'type': 'consu',
            'invoice_policy': 'order',
            'expense_policy': 'cost',
            'default_code': 'CONSU-ORDERED1',
            'service_type': 'manual',
            'taxes_id': False,
            'property_account_expense_id': cls.account_expense_company_B.id,
            'company_id': cls.company_B.id,
        })

        cls.product_deliver_cost_company_B = cls.env['product.product'].create({
            'name': "Delivered at cost",
            'standard_price': 8,
            'list_price': 10,
            'type': 'consu',
            'invoice_policy': 'delivery',
            'expense_policy': 'cost',
            'default_code': 'CONSU-DELI1',
            'service_type': 'manual',
            'taxes_id': False,
            'property_account_expense_id': cls.account_expense_company_B.id,
            'company_id': cls.company_B.id,
        })

        cls.product_order_sales_price_company_B = cls.env['product.product'].create({
            'name': "Ordered at sales price",
            'standard_price': 8,
            'list_price': 10,
            'type': 'consu',
            'invoice_policy': 'order',
            'expense_policy': 'sales_price',
            'default_code': 'CONSU-ORDERED2',
            'service_type': 'manual',
            'taxes_id': False,
            'property_account_expense_id': cls.account_expense_company_B.id,
            'company_id': cls.company_B.id,
        })

        cls.product_deliver_sales_price_company_B = cls.env['product.product'].create({
            'name': "Delivered at sales price",
            'standard_price': 8,
            'list_price': 10,
            'type': 'consu',
            'invoice_policy': 'delivery',
            'expense_policy': 'sales_price',
            'default_code': 'CONSU-DELI2',
            'service_type': 'manual',
            'taxes_id': False,
            'property_account_expense_id': cls.account_expense_company_B.id,
            'company_id': cls.company_B.id,
        })
