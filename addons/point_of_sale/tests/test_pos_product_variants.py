# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged

from odoo.addons.product.tests.common import ProductVariantsCommon


@tagged('post_install', '-at_install')
class TestPoSProductVariants(ProductVariantsCommon):

    def get_ptav(self, template, pav):
        return template.valid_product_template_attribute_line_ids.filtered(
            lambda ptal: ptal.attribute_id == pav.attribute_id
        ).product_template_value_ids.filtered(
            lambda ptav: ptav.product_attribute_value_id == pav
        )

    def test_product_exclusions(self):
        sofa = self.product_template_sofa
        sofa.attribute_line_ids = [Command.create({
            'attribute_id': self.size_attribute.id,
            'value_ids': [Command.set([
                self.size_attribute_s.id,
                self.size_attribute_l.id,
            ])],
        })]

        red_ptav = self.get_ptav(sofa, self.color_attribute_red)
        blue_ptav = self.get_ptav(sofa, self.color_attribute_blue)
        small_ptav = self.get_ptav(sofa, self.size_attribute_s)

        # Create an attribute exclusion for red, small sofas
        red_ptav.exclude_for = [Command.create({
            'product_tmpl_id': sofa.id,
            'value_ids': [Command.set([small_ptav.id])],
        })]

        # Archive blue, small sofa variant
        sofa_blue_s = sofa._get_variant_for_combination(small_ptav + blue_ptav)
        sofa_blue_s.action_archive()

        Product = self.env['product.product']
        unavailable_combinations = Product._get_archived_combinations_per_product_tmpl_id(sofa.ids)
        unavailable_sofas = [set(combination) for combination in unavailable_combinations[sofa.id]]

        self.assertEqual(len(unavailable_sofas), 2, "There should be 2 unavailable combinations")
        self.assertIn(
            {red_ptav.id, small_ptav.id},
            unavailable_sofas,
            "Red, small sofas should be unavailable for sale due to attribute exclusion",
        )
        self.assertIn(
            {blue_ptav.id, small_ptav.id},
            unavailable_sofas,
            "Blue, small sofas should be unavailable for sale due to being archived",
        )
