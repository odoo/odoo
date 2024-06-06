from odoo.fields import Command
from odoo.tests import tagged

from .common import TestSaleCommon


@tagged('post_install', '-at_install')
class TestSaleOrderCreditLimit(TestSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.account_use_credit_limit = True

        buck_currency = cls.env['res.currency'].create({
            'name': 'TB',
            'symbol': 'TB',
        })
        cls.env['res.currency.rate'].create({
            'name': '2023-01-01',
            'rate': 2.0,
            'currency_id': buck_currency.id,
            'company_id': cls.env.company.id,
        })

        cls.buck_pricelist = cls.env['product.pricelist'].create({
            'name': 'Test Buck Pricelist',
            'currency_id': buck_currency.id,
        })

    def test_credit_limit_multicurrency(self):
        self.partner_a.credit_limit = 50

        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'pricelist_id': self.buck_pricelist.id,
            'order_line': [
                Command.create({
                    'product_id': self.company_data['product_order_no'].id,
                    'product_uom_qty': 1,
                    'price_unit': 45.0,
                    'tax_id': False,
                })
            ]
        })
        self.assertEqual(order.amount_total / order.currency_rate, 22.5)
        self.assertEqual(order.partner_credit_warning, '')

        order.write({
            'order_line': [
                Command.create({
                    'product_id': self.company_data['product_order_no'].id,
                    'product_uom_qty': 1,
                    'price_unit': 65.0,
                    'tax_id': False,
                })
            ],
        })
        self.assertEqual(order.amount_total / order.currency_rate, 55)
        self.assertEqual(
            order.partner_credit_warning,
            "partner_a has reached its Credit Limit of : $\xa050.00\n"
            "Total amount due (including this document) : $\xa055.00"
        )
