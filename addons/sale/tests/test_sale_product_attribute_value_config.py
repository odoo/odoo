# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.addons.product.tests.test_product_attribute_value_config import TestProductAttributeValueCommon
from odoo.tests import tagged


class TestSaleProductAttributeValueCommon(TestProductAttributeValueCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env['product.pricelist'].sudo().search([]).action_archive()
        cls.env['product.pricelist'].create({'name': 'Base Pricelist'})

    @classmethod
    def _setup_currency(cls, currency_ratio=2):
        """Get or create a currency. This makes the test non-reliant on demo.

        With an easy currency rate, for a simple 2 ratio in the following tests.
        """
        from_currency = cls.computer.currency_id
        cls._set_or_create_rate_today(from_currency, rate=1)

        to_currency = cls._get_or_create_currency("my currency", "C")
        cls._set_or_create_rate_today(to_currency, currency_ratio)
        return to_currency

    @classmethod
    def _set_or_create_rate_today(cls, currency, rate):
        """Get or create a currency rate for today. This makes the test
        non-reliant on demo data."""
        name = fields.Date.today()
        currency_id = currency.id
        company_id = cls.env.company.id

        CurrencyRate = cls.env['res.currency.rate']

        currency_rate = CurrencyRate.search([
            ('company_id', '=', company_id),
            ('currency_id', '=', currency_id),
            ('name', '=', name),
        ])

        if currency_rate:
            currency_rate.rate = rate
        else:
            CurrencyRate.create({
                'company_id': company_id,
                'currency_id': currency_id,
                'name': name,
                'rate': rate,
            })

    @classmethod
    def _get_or_create_currency(cls, name, symbol):
        """Get or create a currency based on name. This makes the test
        non-reliant on demo data."""
        currency = cls.env['res.currency'].search([('name', '=', name)])
        return currency or currency.create({
            'name': name,
            'symbol': symbol,
        })


@tagged('post_install', '-at_install')
class TestSaleProductAttributeValueConfig(TestSaleProductAttributeValueCommon):
    def _setup_pricelist(self, currency_ratio=2):
        to_currency = self._setup_currency(currency_ratio)

        discount = 10

        pricelist = self.env['product.pricelist'].create({
            'name': 'test pl',
            'currency_id': to_currency.id,
            'company_id': self.computer.company_id.id,
        })

        pricelist_item = self.env['product.pricelist.item'].create({
            'min_quantity': 2,
            'compute_price': 'percentage',
            'percent_price': discount,
            'pricelist_id': pricelist.id,
        })

        return (pricelist, pricelist_item, currency_ratio, 1 - discount / 100)

    def test_01_is_combination_possible_archived(self):
        """The goal is to test the possibility of archived combinations.

        This test could not be put into product module because there was no
        model which had product_id as required and without cascade on delete.
        Here we have the sales order line in this situation.

        This is a necessary condition for `_create_variant_ids` to archive
        instead of delete the variants.
        """
        def do_test(self):
            computer_ssd_256 = self._get_product_template_attribute_value(self.ssd_256)
            computer_ram_8 = self._get_product_template_attribute_value(self.ram_8)
            computer_hdd_1 = self._get_product_template_attribute_value(self.hdd_1)
            computer_hdd_2 = self._get_product_template_attribute_value(self.hdd_2)

            variant = self.computer._get_variant_for_combination(computer_ssd_256 + computer_ram_8 + computer_hdd_1)
            variant2 = self.computer._get_variant_for_combination(computer_ssd_256 + computer_ram_8 + computer_hdd_2)

            self.assertTrue(variant)
            self.assertTrue(variant2)

            # Create a dummy SO to prevent the variant from being deleted by
            # _create_variant_ids() because the variant is a related field that
            # is required on the SO line
            so = self.env['sale.order'].create({'partner_id': 1})
            self.env['sale.order.line'].create({
                'order_id': so.id,
                'name': "test",
                'product_id': variant.id
            })
            # additional variant to test correct ignoring when mismatch values
            self.env['sale.order.line'].create({
                'order_id': so.id,
                'name': "test",
                'product_id': variant2.id
            })

            variant2.active = False
            # CASE: 1 not archived, 2 archived
            self.assertTrue(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_8 + computer_hdd_1))
            self.assertFalse(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_8 + computer_hdd_2))
            # CASE: both archived combination (without no_variant)
            variant.active = False
            self.assertFalse(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_8 + computer_hdd_2))
            self.assertFalse(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_8 + computer_hdd_1))

            # CASE: OK after attribute line removed
            self.computer_hdd_attribute_lines.write({'active': False})
            self.assertTrue(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_8))

            # CASE: not archived (with no_variant)
            self.hdd_attribute.create_variant = 'no_variant'
            self._add_hdd_attribute_line()
            computer_hdd_1 = self._get_product_template_attribute_value(self.hdd_1)
            computer_hdd_2 = self._get_product_template_attribute_value(self.hdd_2)

            self.assertTrue(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_8 + computer_hdd_1))

            # CASE: archived combination found (with no_variant)
            variant = self.computer._get_variant_for_combination(computer_ssd_256 + computer_ram_8 + computer_hdd_1)
            variant.active = False
            self.assertFalse(self.computer._is_combination_possible(computer_ssd_256 + computer_ram_8 + computer_hdd_1))

            # CASE: archived combination has different attributes (including no_variant)
            self.computer_ssd_attribute_lines.write({'active': False})

            variant4 = self.computer._get_variant_for_combination(computer_ram_8 + computer_hdd_1)
            self.env['sale.order.line'].create({
                'order_id': so.id,
                'name': "test",
                'product_id': variant4.id
            })
            self.assertTrue(self.computer._is_combination_possible(computer_ram_8 + computer_hdd_1))

            # CASE: archived combination has different attributes (without no_variant)
            self.computer_hdd_attribute_lines.write({'active': False})
            self.hdd_attribute.create_variant = 'always'
            self._add_hdd_attribute_line()
            computer_ssd_256 = self._get_product_template_attribute_value(self.ssd_256)
            computer_ram_8 = self._get_product_template_attribute_value(self.ram_8)
            computer_hdd_1 = self._get_product_template_attribute_value(self.hdd_1)
            computer_hdd_2 = self._get_product_template_attribute_value(self.hdd_2)

            variant5 = self.computer._get_variant_for_combination(computer_ram_8 + computer_hdd_1)
            self.env['sale.order.line'].create({
                'order_id': so.id,
                'name': "test",
                'product_id': variant5.id
            })

            self.assertTrue(variant4 != variant5)

            self.assertTrue(self.computer._is_combination_possible(computer_ram_8 + computer_hdd_1))

        computer_ssd_256_before = self._get_product_template_attribute_value(self.ssd_256)

        do_test(self)

        # CASE: add back the removed attribute and try everything again
        self.computer_ssd_attribute_lines = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.computer.id,
            'attribute_id': self.ssd_attribute.id,
            'value_ids': [(6, 0, [self.ssd_256.id, self.ssd_512.id])],
        })

        computer_ssd_256_after = self._get_product_template_attribute_value(self.ssd_256)
        self.assertEqual(computer_ssd_256_after, computer_ssd_256_before)
        self.assertEqual(computer_ssd_256_after.attribute_line_id, computer_ssd_256_before.attribute_line_id)
        do_test(self)

    def test_04_create_product_variant_non_dynamic(self):
        """The goal of this test is to make sure the _create_product_variant does
        not create variant if the type is not dynamic. It can however return a
        variant if it already exists."""
        computer_ssd_256 = self._get_product_template_attribute_value(self.ssd_256)
        computer_ram_8 = self._get_product_template_attribute_value(self.ram_8)
        computer_ram_16 = self._get_product_template_attribute_value(self.ram_16)
        computer_hdd_1 = self._get_product_template_attribute_value(self.hdd_1)
        self._add_exclude(computer_ram_16, computer_hdd_1)

        # CASE: variant is already created, it should return it
        combination = computer_ssd_256 + computer_ram_8 + computer_hdd_1
        variant1 = self.computer._get_variant_for_combination(combination)
        self.assertEqual(self.computer._create_product_variant(combination), variant1)

        # CASE: variant does not exist, but template is non-dynamic, so it
        # should not create it
        Product = self.env['product.product']
        variant1.unlink()
        self.assertEqual(self.computer._create_product_variant(combination), Product)

    def test_05_create_product_variant_dynamic(self):
        """The goal of this test is to make sure the _create_product_variant does
        work with dynamic. If the combination is possible, it should create it.
        If it's not possible, it should not create it."""
        self.computer_hdd_attribute_lines.write({'active': False})
        self.hdd_attribute.create_variant = 'dynamic'
        self._add_hdd_attribute_line()

        computer_ssd_256 = self._get_product_template_attribute_value(self.ssd_256)
        computer_ram_8 = self._get_product_template_attribute_value(self.ram_8)
        computer_ram_16 = self._get_product_template_attribute_value(self.ram_16)
        computer_hdd_1 = self._get_product_template_attribute_value(self.hdd_1)
        self._add_exclude(computer_ram_16, computer_hdd_1)

        # CASE: variant does not exist, but combination is not possible
        # so it should not create it
        impossible_combination = computer_ssd_256 + computer_ram_16 + computer_hdd_1
        Product = self.env['product.product']
        self.assertEqual(self.computer._create_product_variant(impossible_combination), Product)

        # CASE: the variant does not exist, and the combination is possible, so
        # it should create it
        combination = computer_ssd_256 + computer_ram_8 + computer_hdd_1
        variant = self.computer._create_product_variant(combination)
        self.assertTrue(variant)

        # CASE: the variant already exists, so it should return it
        self.assertEqual(variant, self.computer._create_product_variant(combination))

    def _add_keyboard_attribute(self):
        self.keyboard_attribute = self.env['product.attribute'].create({
            'name': 'Keyboard',
            'sequence': 6,
            'create_variant': 'dynamic',
        })
        self.keyboard_included = self.env['product.attribute.value'].create({
            'name': 'Included',
            'attribute_id': self.keyboard_attribute.id,
            'sequence': 1,
        })
        self.keyboard_excluded = self.env['product.attribute.value'].create({
            'name': 'Excluded',
            'attribute_id': self.keyboard_attribute.id,
            'sequence': 2,
        })
        self.computer_keyboard_attribute_lines = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.computer.id,
            'attribute_id': self.keyboard_attribute.id,
            'value_ids': [(6, 0, [self.keyboard_included.id, self.keyboard_excluded.id])],
        })
        self.computer_keyboard_attribute_lines.product_template_value_ids[0].price_extra = 5
        self.computer_keyboard_attribute_lines.product_template_value_ids[1].price_extra = -5
