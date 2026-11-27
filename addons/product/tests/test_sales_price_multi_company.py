# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.product.tests.common import ProductVariantsCommon


@tagged('post_install', '-at_install')
class TestSalesPriceMultiCompany(ProductVariantsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_a = cls.env['res.company']._get_main_company()
        cls.company_b, cls.company_c = cls.env['res.company'].sudo().create([
            {'name': "Company B"},
            {'name': "Company C"},
        ])
        cls._test_user.sudo().company_ids = [
            Command.link(company.id) for company in cls.company_b + cls.company_c
        ]

        cls.template = cls.env['product.template'].with_company(cls.company_a).create({
            'name': "Chair",
            'list_price': 100.0,
            'attribute_line_ids': [Command.create({
                'attribute_id': cls.size_attribute.id,
                'value_ids': [Command.set(cls.size_attribute.value_ids.ids)],
            })],
        })
        cls.variant_s, cls.variant_m, cls.variant_l = cls.template.product_variant_ids

    def test_new_product_price_is_set_in_all_companies(self):
        for company in self.company_b + self.company_c:
            self.assertEqual(self.variant_s.with_company(company).lst_price, 100.0)

    def test_company_price_does_not_change_other_companies(self):
        self.template.with_company(self.company_b).list_price = 140.0
        for company, price in (
            (self.company_a, 100.0),
            (self.company_b, 140.0),
            (self.company_c, 100.0),
        ):
            self.assertEqual(self.variant_s.with_company(company).lst_price, price)

    def test_variant_prices_are_kept_per_company(self):
        self.variant_m.with_company(self.company_a).lst_price = 200.0
        self.variant_m.with_company(self.company_b).lst_price = 250.0
        for company, price in (
            (self.company_a, 200.0),
            (self.company_b, 250.0),
            (self.company_c, 100.0),
        ):
            self.assertEqual(self.variant_m.with_company(company).lst_price, price)

    def test_extra_price_applies_in_all_companies(self):
        ptav = self.template.attribute_line_ids.product_template_value_ids.filtered(
            lambda ptav: ptav.product_attribute_value_id == self.size_attribute_m
        )
        ptav.price_extra = 10.0
        for company in self.company_a + self.company_b + self.company_c:
            self.assertEqual(self.variant_m.with_company(company).lst_price, 110.0)

    def test_search_uses_company_price(self):
        self.template.with_company(self.company_b).list_price = 140.0
        products = self.env['product.template'].with_company(self.company_b).search([
            ('id', '=', self.template.id), ('list_price', '=', 140.0),
        ])
        self.assertEqual(products, self.template)
