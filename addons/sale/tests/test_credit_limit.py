from odoo.addons.sale.tests.common import SaleCommon
from odoo.fields import Command
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSaleOrderCreditLimit(SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.account_use_credit_limit = True

        buck_currency = cls.env['res.currency'].create({
            'name': 'Test Buck ',
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
        self.partner.use_partner_credit_limit = True
        self.partner.credit_limit = 50

        self.product.lst_price = 45

        order = self.empty_order
        order.pricelist_id = self.buck_pricelist

        self.empty_order.order_line = [
            Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 1.0,
            }),
        ]
        self.assertEqual(order.partner_credit_warning, '')
