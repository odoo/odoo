# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.product.tests.common import ProductCommon
from odoo.addons.sales_team.tests.common import SalesTeamCommon


class SaleCommon(
    ProductCommon, # BaseCommon, UomCommon
    SalesTeamCommon,
):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.country_id = cls.quick_ref('base.us')

        # Not defined in product common because only used in sale
        cls.group_discount_per_so_line = cls.quick_ref('sale.group_discount_per_so_line')

        (cls.product + cls.service_product).write({
            'taxes_id': [Command.clear()],
        })

        cls.empty_order, cls.sale_order = cls.env['sale.order'].create([
            {
                'partner_id': cls.partner.id,
            }, {
                'partner_id': cls.partner.id,
                'order_line': [
                    Command.create({
                        'product_id': cls.product.id,
                        'product_uom_qty': 5.0,
                    }),
                    Command.create({
                        'product_id': cls.service_product.id,
                        'product_uom_qty': 12.5,
                    })
                ]
            },
        ])

    @classmethod
    def _enable_discounts(cls):
        cls.env.user.groups_id += cls.group_discount_per_so_line


class TestSaleCommon(AccountTestInvoicingCommon):

    @classmethod
    def collect_company_accounting_data(cls, company):
        company_data = super().collect_company_accounting_data(company)

    @classmethod
    def setup_sale_configuration_for_company(cls, company):
        Users = cls.env['res.users'].with_context(no_reset_password=True).sudo()

        company_data = {
            # Sales Team
            'default_sale_team': cls.env['crm.team'].with_context(tracking_disable=True).sudo().create({
                'name': 'Test Channel',
                'company_id': company.id,
            }),

        company_data.update({
            # Users
            'default_user_salesman': cls.env['res.users'].create({
                'name': 'default_user_salesman',
                'login': 'default_user_salesman.comp%s' % company.id,
                'email': 'default_user_salesman@example.com',
                'signature': '--\nMark',
                'notification_type': 'email',
                'groups_id': [(6, 0, cls.quick_ref('sales_team.group_sale_salesman').ids)],
                'company_ids': [(6, 0, company.ids)],
                'company_id': company.id,
            }),

            # Products
            'product_service_delivery': cls.env['product.product'].with_company(company).create({
                'name': 'product_service_delivery',
                'categ_id': cls.product_category.id,
                'standard_price': 200.0,
                'list_price': 180.0,
                'type': 'service',
                'uom_id': cls.uom_unit.id,
                'uom_po_id': cls.uom_unit.id,
                'default_code': 'SERV_DEL',
                'invoice_policy': 'delivery',
                'taxes_id': [(6, 0, [])],
                'supplier_taxes_id': [(6, 0, [])],
                'company_id': company.id,
            }),
            'product_service_order': cls.env['product.product'].with_company(company).create({
                'name': 'product_service_order',
                'categ_id': cls.product_category.id,
                'standard_price': 40.0,
                'list_price': 90.0,
                'type': 'service',
                'uom_id': cls.uom_hour.id,
                'uom_po_id': cls.uom_hour.id,
                'description': 'Example of product to invoice on order',
                'default_code': 'PRE-PAID',
                'invoice_policy': 'order',
                'taxes_id': [(6, 0, [])],
                'supplier_taxes_id': [(6, 0, [])],
                'company_id': company.id,
            }),
            'product_order_cost': cls.env['product.product'].with_company(company).create({
                'name': 'product_order_cost',
                'categ_id': cls.product_category.id,
                'standard_price': 235.0,
                'list_price': 280.0,
                'type': 'consu',
                'weight': 0.01,
                'uom_id': cls.uom_unit.id,
                'uom_po_id': cls.uom_unit.id,
                'default_code': 'FURN_9999',
                'invoice_policy': 'order',
                'expense_policy': 'cost',
                'taxes_id': [(6, 0, [])],
                'supplier_taxes_id': [(6, 0, [])],
                'company_id': company.id,
            }),
            'product_delivery_cost': cls.env['product.product'].with_company(company).create({
                'name': 'product_delivery_cost',
                'categ_id': cls.product_category.id,
                'standard_price': 55.0,
                'list_price': 70.0,
                'type': 'consu',
                'weight': 0.01,
                'uom_id': cls.uom_unit.id,
                'uom_po_id': cls.uom_unit.id,
                'default_code': 'FURN_7777',
                'invoice_policy': 'delivery',
                'expense_policy': 'cost',
                'taxes_id': [(6, 0, [])],
                'supplier_taxes_id': [(6, 0, [])],
                'company_id': company.id,
            }),
            'product_order_sales_price': cls.env['product.product'].with_company(company).create({
                'name': 'product_order_sales_price',
                'categ_id': cls.product_category.id,
                'standard_price': 235.0,
                'list_price': 280.0,
                'type': 'consu',
                'weight': 0.01,
                'uom_id': cls.uom_unit.id,
                'uom_po_id': cls.uom_unit.id,
                'default_code': 'FURN_9999',
                'invoice_policy': 'order',
                'expense_policy': 'sales_price',
                'taxes_id': [(6, 0, [])],
                'supplier_taxes_id': [(6, 0, [])],
                'company_id': company.id,
            }),
            'product_delivery_sales_price': cls.env['product.product'].with_company(company).create({
                'name': 'product_delivery_sales_price',
                'categ_id': cls.product_category.id,
                'standard_price': 55.0,
                'list_price': 70.0,
                'type': 'consu',
                'weight': 0.01,
                'uom_id': cls.uom_unit.id,
                'uom_po_id': cls.uom_unit.id,
                'default_code': 'FURN_7777',
                'invoice_policy': 'delivery',
                'expense_policy': 'sales_price',
                'taxes_id': [(6, 0, [])],
                'supplier_taxes_id': [(6, 0, [])],
                'company_id': company.id,
            }),
            'product_order_no': cls.env['product.product'].with_company(company).create({
                'name': 'product_order_no',
                'categ_id': cls.product_category.id,
                'standard_price': 235.0,
                'list_price': 280.0,
                'type': 'consu',
                'weight': 0.01,
                'uom_id': cls.uom_unit.id,
                'uom_po_id': cls.uom_unit.id,
                'default_code': 'FURN_9999',
                'invoice_policy': 'order',
                'expense_policy': 'no',
                'taxes_id': [(6, 0, [])],
                'supplier_taxes_id': [(6, 0, [])],
                'company_id': company.id,
            }),
            'product_delivery_no': cls.env['product.product'].with_company(company).create({
                'name': 'product_delivery_no',
                'categ_id': cls.product_category.id,
                'standard_price': 55.0,
                'list_price': 70.0,
                'type': 'consu',
                'weight': 0.01,
                'uom_id': cls.uom_unit.id,
                'uom_po_id': cls.uom_unit.id,
                'default_code': 'FURN_7777',
                'invoice_policy': 'delivery',
                'expense_policy': 'no',
                'taxes_id': [(6, 0, [])],
                'supplier_taxes_id': [(6, 0, [])],
                'company_id': company.id,
            }),
        })

        return company_data

    @classmethod
    def _enable_sale_salesman(cls):
        """ Required to confirm a sale order """
        cls.user.groups_id += cls.env.ref('sales_team.group_sale_salesman')

    @classmethod
    def _enable_sale_manager(cls):
        cls.user.groups_id += cls.env.ref('sales_team.group_sale_manager')


class TestSaleCommon(AccountTestInvoicingCommon, TestSaleCommonBase):
    ''' Setup to be used post-install with sale and accounting test configuration.'''

    @classmethod
    def collect_company_accounting_data(cls, company):
        company_data = super().collect_company_accounting_data(company)

        company_data.update(cls.setup_sale_configuration_for_company(company_data['company']))

        company_data['product_category'].write({
            'property_account_income_categ_id': company_data['default_account_revenue'].id,
            'property_account_expense_categ_id': company_data['default_account_expense'].id,
        })

        return company_data
>>>>>>> 46ba20461bb9 ([REF] test: address code review comments)
