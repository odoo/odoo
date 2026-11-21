# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.product.tests.common import ProductVariantsCommon


@tagged('post_install', '-at_install')
class TestPricelistRuleResolution(ProductVariantsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.groups_id += cls.env.ref('product.group_product_pricelist')

        Category = cls.env['product.category']
        cls.child_category = Category.create({
            'name': "Child", 'parent_id': cls.product_category.id,
        })
        cls.grandchild_category = Category.create({
            'name': "Grandchild", 'parent_id': cls.child_category.id,
        })
        cls.other_category = Category.create({'name': "Other"})

        Template = cls.env['product.template']
        cls.multi_tmpl = Template.create({
            'name': "Multi variants",
            'list_price': 100,
            'categ_id': cls.grandchild_category.id,
            'attribute_line_ids': [Command.create({
                'attribute_id': cls.color_attribute.id,
                'value_ids': [Command.set(cls.color_attribute.value_ids.ids)],
            })],
        })
        cls.single_tmpl, cls.child_tmpl, cls.other_tmpl, cls.plain_tmpl = Template.create([
            {'name': "Single variant", 'list_price': 50, 'categ_id': cls.child_category.id},
            {'name': "Child", 'list_price': 60, 'categ_id': cls.child_category.id},
            {'name': "Other", 'list_price': 70, 'categ_id': cls.other_category.id},
            {'name': "Plain", 'list_price': 80, 'categ_id': cls.grandchild_category.id},
        ])
        cls.templates = cls.multi_tmpl + cls.single_tmpl + cls.child_tmpl + cls.other_tmpl \
            + cls.plain_tmpl
        cls.variants = cls.templates.product_variant_ids

        yesterday = fields.Datetime.now() - timedelta(days=1)
        cls.pricelist = cls._create_pricelist(item_ids=[
            # Restricted to a variant
            Command.create({
                'applied_on': '0_product_variant',
                'product_id': cls.multi_tmpl.product_variant_ids[0].id,
                'compute_price': 'fixed',
                'fixed_price': 11,
            }),
            # Restricted to the variant of a single variant template: applies to the template
            Command.create({
                'applied_on': '0_product_variant',
                'product_id': cls.single_tmpl.product_variant_id.id,
                'compute_price': 'fixed',
                'fixed_price': 12,
            }),
            # Restricted to a product, from a minimum quantity
            Command.create({
                'applied_on': '1_product',
                'product_tmpl_id': cls.multi_tmpl.id,
                'min_quantity': 5,
                'compute_price': 'fixed',
                'fixed_price': 13,
            }),
            Command.create({
                'applied_on': '1_product',
                'product_tmpl_id': cls.other_tmpl.id,
                'compute_price': 'fixed',
                'fixed_price': 14,
            }),
            # Expired
            Command.create({
                'applied_on': '1_product',
                'product_tmpl_id': cls.plain_tmpl.id,
                'date_end': yesterday,
                'compute_price': 'fixed',
                'fixed_price': 15,
            }),
            # Restricted to categories, applying to their children
            Command.create({
                'applied_on': '2_product_category',
                'categ_id': cls.grandchild_category.id,
                'min_quantity': 5,
                'compute_price': 'discount',
                'price_discount': 20,
            }),
            Command.create({
                'applied_on': '2_product_category',
                'categ_id': cls.product_category.id,
                'compute_price': 'discount',
                'price_discount': 10,
            }),
            # Not restricted
            Command.create({
                'applied_on': '3_global',
                'compute_price': 'discount',
                'price_discount': 5,
            }),
        ])

    def test_batch_matches_single_product(self):
        """Pricing products together gives the same rule and price as pricing them one by one."""
        for records in (self.templates, self.variants):
            for quantity in (1, 10):
                with self.subTest(model=records._name, quantity=quantity):
                    batch = self.pricelist._compute_price_rule(records, quantity)
                    single = {
                        record.id: self.pricelist._compute_price_rule(record, quantity)[record.id]
                        for record in records
                    }
                    self.assertEqual(batch, single)

    def test_batch_applied_rules(self):
        """Each product gets the first rule that applies to it, in order of precedence."""
        rules = self.pricelist.item_ids
        variant_rule, single_variant_rule, multi_rule, other_rule = rules.filtered(
            lambda r: r.applied_on in ('0_product_variant', '1_product') and not r.date_end
        ).sorted(lambda r: (r.applied_on, r.fixed_price))
        grandchild_rule = rules.filtered(lambda r: r.categ_id == self.grandchild_category)
        parent_rule = rules.filtered(lambda r: r.categ_id == self.product_category)
        multi_variant = self.multi_tmpl.product_variant_ids[0]
        expected = [
            # (record, quantity, rule)
            (self.multi_tmpl, 1, parent_rule),  # several variants, minimums not reached
            (self.multi_tmpl, 10, multi_rule),
            (self.single_tmpl, 1, single_variant_rule),
            (self.child_tmpl, 1, parent_rule),
            (self.other_tmpl, 1, other_rule),
            (self.plain_tmpl, 1, parent_rule),  # the product rule is expired
            (self.plain_tmpl, 10, grandchild_rule),
            (multi_variant, 1, variant_rule),
            (multi_variant, 10, variant_rule),
            (self.multi_tmpl.product_variant_ids[1], 10, multi_rule),
            (self.single_tmpl.product_variant_id, 1, single_variant_rule),
            (self.other_tmpl.product_variant_id, 1, other_rule),
        ]
        for quantity in (1, 10):
            prices = {
                'product.template': self.pricelist._compute_price_rule(self.templates, quantity),
                'product.product': self.pricelist._compute_price_rule(self.variants, quantity),
            }
            for record, expected_quantity, rule in expected:
                if expected_quantity == quantity:
                    with self.subTest(record=record.display_name, quantity=quantity):
                        self.assertEqual(prices[record._name][record.id][1], rule.id)

    def test_only_check_rules_that_may_apply(self):
        """A product is only checked against the rules that may apply to it, not against the
        rules restricted to the other products."""
        templates = self.env['product.template'].create([
            {'name': f"Product {i}", 'categ_id': self.other_category.id} for i in range(20)
        ])
        pricelist = self._create_pricelist(item_ids=[
            Command.create({
                'applied_on': '1_product',
                'product_tmpl_id': template.id,
                'compute_price': 'fixed',
                'fixed_price': 10,
            })
            for template in templates
        ])

        PricelistItem = self.env.registry['product.pricelist.item']
        is_applicable_for = PricelistItem._is_applicable_for
        checks = []

        def _is_applicable_for(rule, product, *args, **kwargs):
            checks.append((rule.product_tmpl_id, product))
            return is_applicable_for(rule, product, *args, **kwargs)

        with patch.object(PricelistItem, '_is_applicable_for', _is_applicable_for):
            pricelist._compute_price_rule(templates, 1)
        # Each product is only checked against its own rule, instead of the rules of the other
        # products ordered before it
        self.assertEqual(checks, [(template, template) for template in templates])
