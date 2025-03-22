# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import Form, tagged, users

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

        cls.sales_user = cls.company_data['default_user_salesman']
        cls.sales_user.write({
            'login': "notaccountman",
            'email': "bad@accounting.com",
        })

        cls.empty_order = cls.env['sale.order'].create({
            'partner_id': cls.partner_a.id,
        })

    def test_credit_limit_multicurrency(self):
        self.partner_a.credit_limit = 50

        order = self.empty_order
        order.write({
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

    @users('notaccountman')
    def test_credit_limit_access(self):
        """Ensure credit warning gets displayed without Accounting access."""
        self.empty_order.user_id = self.env.user
        self.empty_order.partner_id.credit_limit = self.product_a.list_price

        for group in self.partner_a._fields['credit'].groups.split(','):
            self.assertFalse(self.env.user.has_group(group))

        with Form(self.empty_order.with_env(self.env)) as order_form:
            with order_form.order_line.new() as sol:
                sol.product_id = self.product_a
                sol.tax_id.clear()
            self.assertFalse(
                order_form.partner_credit_warning,
                "No credit warning should be displayed (yet)",
            )
            with order_form.order_line.edit(0) as sol:
                sol.tax_id.add(self.product_a.taxes_id)
            self.assertTrue(
                order_form.partner_credit_warning,
                "Credit warning should be displayed",
            )
