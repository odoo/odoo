import time

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon


@tagged('post_install', '-at_install')
class TestSubscriptionMultiCompany(TestSubscriptionCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner.property_product_pricelist = cls.env['product.pricelist'].create({
            'name': "Test Pricelist",
            'sequence': 4,
        })
        cls.new_currency = cls.env['res.currency'].create({
            'name': 'New Currency',
            'symbol': ':)',
            'rate_ids': [Command.create({'rate': .5, 'name': time.strftime('%Y-%m-%d')})],
        })
        cls.pricelist_new_currency = cls.env['product.pricelist'].create({
            'name': 'New Currency pricelist',
            'currency_id': cls.new_currency.id,
            'sequence': 2,
        })
        cls.partner_new_currency = cls.env['res.partner'].create({
            'name': 'New Currency partner',
            'property_product_pricelist': cls.pricelist_new_currency.id,
        })
        cls.company_2 = cls.env['res.company'].create({
            'name': 'Company 2', 'currency_id': cls.new_currency.id
        })
        cls.env.company.currency_id.with_company(cls.company_2).rate_ids = [
            Command.create({'rate': 2, 'name': time.strftime('%Y-%m-%d')})
        ]


    def test_basic_price_computation_multicurrency_multicompany(self):
        """" Testing different setups with same product from the main company"""

        # With pricelists from same currency as company
        base_so_company_1 = self.env['sale.order'].create({'partner_id': self.partner.id})
        base_sol_company_1 = self.env['sale.order.line'].create({
            'product_id': self.product.id,
            'order_id': base_so_company_1.id,
        })
        base_so_company_2 = self.env['sale.order'].with_company(self.company_2).create({
            'partner_id': self.partner_new_currency.id,
        })
        base_sol_company_2 = self.env['sale.order.line'].create({
            'product_id': self.product.id,
            'order_id': base_so_company_2.id,
        })
        self.assertAlmostEqual(base_sol_company_1.price_unit, base_sol_company_2.price_unit*2,
                               msg="conversion rate should be applied")

        # With pricelists from different currency as company
        so_company_1_new_currency_pl = self.env['sale.order'].create(
            {'partner_id': self.partner_new_currency.id}
        )
        sol_company_1_new_currency_pl = self.env['sale.order.line'].create({
            'product_id': self.product.id,
            'order_id': so_company_1_new_currency_pl.id,
        })
        so_company_2_base_currency_pl = self.env['sale.order'].create(
            {'partner_id': self.partner.id}
        )
        sol_company_2_base_currency_pl = self.env['sale.order.line'].create({
            'product_id': self.product.id,
            'order_id': so_company_2_base_currency_pl.id,
        })
        self.assertEqual(sol_company_1_new_currency_pl.price_unit, base_sol_company_2.price_unit)
        self.assertEqual(sol_company_2_base_currency_pl.price_unit, base_sol_company_1.price_unit)

        # Checking that the computation without pricelist is the same as with empty pricelist
        self.env['product.pricelist'].search([('active', '=', True)]).action_archive()
        so_company_1_no_pl = self.env['sale.order'].create({'partner_id': self.partner.id})
        sol_company_1_no_pl = self.env['sale.order.line'].create({
            'product_id': self.product.id,
            'order_id': so_company_1_no_pl.id,
        })
        so_company_2_no_pl = self.env['sale.order'].with_company(self.company_2).create({
            'partner_id': self.partner_new_currency.id,
        })
        sol_company_2_no_pl = self.env['sale.order.line'].create({
            'product_id': self.product.id,
            'order_id': so_company_2_no_pl.id,
        })
        self.assertEqual(sol_company_1_no_pl.price_unit, base_sol_company_1.price_unit)
        self.assertEqual(sol_company_2_no_pl.price_unit, base_sol_company_2.price_unit)
