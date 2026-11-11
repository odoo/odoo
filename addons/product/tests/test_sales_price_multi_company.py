# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.product.tests.common import ProductVariantsCommon


@tagged('post_install', '-at_install')
class TestSalesPriceMultiCompany(ProductVariantsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.main_company = cls.env['res.company']._get_main_company()
        cls.company_b, cls.company_c = cls.env['res.company'].sudo().create([
            {'name': "Company B"},
            {'name': "Company C"},
        ])
        cls.branch_b = cls.env['res.company'].sudo().create({
            'name': "Branch B", 'parent_id': cls.company_b.id,
        })
        companies = cls.main_company + cls.company_b + cls.company_c + cls.branch_b
        cls._test_user.sudo().company_ids = [Command.link(company.id) for company in companies]

        cls.template = cls.env['product.template'].with_company(cls.main_company).create({
            'name': "Chair",
            'list_price': 100.0,
            'attribute_line_ids': [Command.create({
                'attribute_id': cls.size_attribute.id,
                'value_ids': [Command.set(cls.size_attribute.value_ids.ids)],
            })],
        })
        cls.variant_s, cls.variant_m, cls.variant_l = cls.template.product_variant_ids

    def test_company_price_applies_to_that_company_and_its_branches_only(self):
        self.template.with_company(self.company_b).list_price = 140.0
        for company, price in (
            (self.main_company, 100.0),
            (self.company_b, 140.0),
            (self.branch_b, 140.0),
            (self.company_c, 100.0),
        ):
            self.assertEqual(self.template.with_company(company).list_price, price)

    def test_reset_company_price_falls_back_to_main_company(self):
        self.template.with_company(self.company_b).list_price = 140.0
        self.template.with_company(self.company_b).list_price = 0.0
        self.assertEqual(self.template.with_company(self.company_b).list_price, 100.0)

    def test_main_company_variant_price_applies_to_companies_without_price(self):
        self.variant_s.with_company(self.main_company).lst_price = 150.0
        self.assertEqual(self.variant_s.with_company(self.company_c).lst_price, 150.0)

    def test_variant_set_back_to_computed_price_follows_template(self):
        self.variant_s.lst_price = 150.0
        self.variant_s.lst_price = 100.0
        self.template.list_price = 120.0
        self.assertEqual(self.variant_s.lst_price, 120.0)

    def test_extra_price_change_resets_variant_prices_in_all_companies(self):
        self.variant_m.with_company(self.main_company).lst_price = 300.0
        self.variant_m.with_company(self.company_b).lst_price = 310.0
        self.variant_m.product_template_attribute_value_ids.price_extra = 5.0
        for company in self.main_company + self.company_b:
            self.assertEqual(self.variant_m.with_company(company).lst_price, 105.0)

    def test_search_uses_company_price(self):
        self.template.with_company(self.company_b).list_price = 140.0
        products = self.env['product.template'].with_company(self.company_b).search([
            ('id', '=', self.template.id), ('list_price', '=', 140.0),
        ])
        self.assertEqual(products, self.template)
