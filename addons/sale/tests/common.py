# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command

from odoo.addons.account.tests.common import AccountTestInvoicingCommon, TestTaxCommon
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
        cls._enable_pricelists()
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
        cls.env.user.group_ids += cls.group_discount_per_so_line

    def _create_so(self, **values):
        default_values = {
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                }),
            ],
            **values
        }
        return self.env['sale.order'].create(default_values)


class TestSaleCommon(AccountTestInvoicingCommon):

    @classmethod
    def collect_company_accounting_data(cls, company):
        company_data = super().collect_company_accounting_data(company)

        company_data.update({
            # Users
            'default_user_salesman': cls.env['res.users'].create({
                'name': 'default_user_salesman',
                'login': 'default_user_salesman.comp%s' % company.id,
                'email': 'default_user_salesman@example.com',
                'signature': '--\nMark',
                'notification_type': 'email',
                'group_ids': [(6, 0, cls.quick_ref('sales_team.group_sale_salesman').ids)],
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
    def get_default_groups(cls):
        groups = super().get_default_groups()
        return groups | cls.quick_ref('sales_team.group_sale_manager')


class TestTaxCommonSale(TestSaleCommon, TestTaxCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.foreign_currency_pricelist = cls.env['product.pricelist'].create({
            'name': "TestTaxCommonSale",
            'currency_id': cls.foreign_currency.id,
            'company_id': cls.env.company.id,
        })

    def convert_document_to_sale_order(self, document):
        order_date = '2020-01-01'
        currency = document['currency']
        self._ensure_rate(currency, order_date, document['rate'])
        self.foreign_currency_pricelist.currency_id = currency
        return self.env['sale.order'].create({
            'date_order': order_date,
            'currency_id': currency.id,
            'partner_id': self.partner_a.id,
            'pricelist_id': self.foreign_currency_pricelist.id,
            'order_line': [
                Command.create({
                    'name': str(i),
                    'product_id': (base_line['product_id'] or self.product_a).id,
                    'price_unit': base_line['price_unit'],
                    'discount': base_line['discount'],
                    'product_uom_qty': base_line['quantity'],
                    'tax_ids': [Command.set(base_line['tax_ids'].ids)],
                })
                for i, base_line in enumerate(document['lines'])
            ],
        })

    def assert_sale_order_tax_totals_summary(self, sale_order, expected_values, soft_checking=False):
        self._assert_tax_totals_summary(sale_order.tax_totals, expected_values, soft_checking=soft_checking)
        cash_rounding_base_amount_currency = sale_order.tax_totals.get('cash_rounding_base_amount_currency', 0.0)
        expected_amounts = {}
        if 'base_amount_currency' in expected_values:
            expected_amounts['amount_untaxed'] = expected_values['base_amount_currency'] + cash_rounding_base_amount_currency
        if 'tax_amount_currency' in expected_values:
            expected_amounts['amount_tax'] = expected_values['tax_amount_currency']
        if 'total_amount_currency' in expected_values:
            expected_amounts['amount_total'] = expected_values['total_amount_currency']
        self.assertRecordValues(sale_order, [expected_amounts])
