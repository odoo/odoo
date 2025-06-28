# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from collections import defaultdict
from functools import reduce

from odoo import models
from odoo.tools import populate

_logger = logging.getLogger(__name__)


class ProductAttribute(models.Model):
    _inherit = "product.attribute"
    _populate_sizes = {"small": 20, "medium": 150, "large": 750}

    def _populate(self, size):

        # Reflect the settings with data created
        self.env['res.config.settings'].create({
            'group_product_variant': True,  # Activate variant
        }).execute()

        return super()._populate(size)

    def _populate_factories(self):
        return [
            ("name", populate.constant('PA_{counter}')),
            ("sequence", populate.randomize([False] + [i for i in range(1, 101)])),
            ("create_variant", populate.randomize(["always", "dynamic", "no_variant"])),
        ]


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"
    _populate_dependencies = ["product.attribute"]
    _populate_sizes = {"small": 100, "medium": 1_000, "large": 10_000}

    def _populate_factories(self):
        attribute_ids = self.env.registry.populated_models["product.attribute"]

        return [
            ("name", populate.constant('PAV_{counter}')),
            ("sequence", populate.randomize([False] + [i for i in range(1, 101)])),
            ("attribute_id", populate.randomize(attribute_ids)),
        ]


class ProductTemplate(models.Model):
    _inherit = "product.template"
    _populate_sizes = {"small": 150, "medium": 5_000, "large": 50_000}
    _populate_dependencies = ["product.attribute.value", "product.category"]

    def _populate(self, size):
        res = super()._populate(size)

        def set_barcode_variant(sample_ratio):
            random = populate.Random('barcode_product_template')
            product_variants_ids = res.product_variant_ids.ids
            product_variants_ids = random.sample(product_variants_ids, int(len(product_variants_ids) * sample_ratio))
            product_variants = self.env['product.product'].browse(product_variants_ids)
            _logger.info('Set barcode on product variants (%s)', len(product_variants))
            for product in product_variants:
                product.barcode = "BARCODE-PT-%s" % product.id

        set_barcode_variant(0.85)

        return res

    def _populate_factories(self):
        attribute_ids = self.env.registry.populated_models["product.attribute"]
        attribute_ids_by_types = defaultdict(list)
        attributes = self.env["product.attribute"].browse(attribute_ids)
        for attr in attributes:
            attribute_ids_by_types[attr.create_variant].append(attr.id)

        def get_attributes(values, counter, random):
            if random.random() < 0.20:  # 20 % chance to have no attributes
                return False
            attributes_qty = random.choices(
                [1, 2, 3, 4, 5, 6, 8, 10],
                [10, 9, 8, 7, 6, 4, 1, 0.5],
            )[0]
            attr_line_vals = []
            attribute_used_ids = attribute_ids
            if random.random() < 0.20:  # 20 % chance of using only always attributes (to test when product has lot of variant)
                attribute_used_ids = attribute_ids_by_types["always"]

            no_variant = False
            values_count = [0 for i in range(attributes_qty)]

            def will_exceed(i):
                return not no_variant and reduce((lambda x, y: (x or 1) * (y or 1)), values_count[i:] + [values_count[i] + 1] + values_count[:i]) > 1000

            for i in range(attributes_qty):
                if will_exceed(i):
                    return attr_line_vals
                attr_id = random.choice(attribute_used_ids)
                attr = self.env["product.attribute"].browse(attr_id)
                if attr.create_variant == "dynamic":
                    no_variant = True
                if not attr.value_ids:
                    # attribute without any value
                    continue
                nb_values = len(attr.value_ids)
                vals_qty = random.randrange(nb_values) + 1
                value_ids = set()
                for __ in range(vals_qty):
                    # Ensure that we wouldn't have > 1k variants with the generated attributes combination
                    if will_exceed(i):
                        break
                    random_value_id = attr.value_ids[random.randrange(nb_values)].id
                    if random_value_id not in value_ids:
                        values_count[i] += 1
                        value_ids.add(random_value_id)

                attr_line_vals.append((0, 0, {
                    "attribute_id": attr_id,
                    "value_ids": [(6, 0, list(value_ids))],
                }))

            return attr_line_vals

        return [
            ("name", populate.constant('product_template_name_{counter}')),
            ("description", populate.constant('product_template_description_{counter}')),
            ("default_code", populate.constant('PT-{counter}')),
            ("attribute_line_ids", populate.compute(get_attributes)),
        ] + self.env['product.product']._populate_get_product_factories()


class ProductTemplateAttributeExclusion(models.Model):
    _inherit = "product.template.attribute.exclusion"
    _populate_dependencies = ["product.template"]
    _populate_sizes = {"small": 200, "medium": 1_000, "large": 5_000}

    def _populate_factories(self):
        p_tmpl_ids = self.env.registry.populated_models["product.template"]

        configurable_templates = self.env["product.template"].search([
            ('id', 'in', p_tmpl_ids),
            ('has_configurable_attributes', '=', True),
        ])
        tmpl_ids_possible = []
        multi_values_attribute_lines_by_tmpl = {}
        for template in configurable_templates:
            multi_values_attribute_lines = template.attribute_line_ids.filtered(
                lambda l: len(l.value_ids) > 1
            )
            if len(multi_values_attribute_lines) < 2:
                continue
            tmpl_ids_possible.append(template.id)
            multi_values_attribute_lines_by_tmpl[template.id] = multi_values_attribute_lines

        def get_product_template_attribute_value_id(values, counter, random):
            return random.choice(multi_values_attribute_lines_by_tmpl[values['product_tmpl_id']].product_template_value_ids.ids)

        def get_value_ids(values, counter, random):
            attr_val = self.env['product.template.attribute.value'].browse(values['product_template_attribute_value_id']).attribute_line_id
            remaining_lines = multi_values_attribute_lines_by_tmpl[values['product_tmpl_id']] - attr_val
            return [(
                # TODO: multiple values
                6, 0, [random.choice(remaining_lines.product_template_value_ids).id]
            )]

        return [
            ("product_tmpl_id", populate.randomize(tmpl_ids_possible)),
            ("product_template_attribute_value_id", populate.compute(get_product_template_attribute_value_id)),
            ("value_ids", populate.compute(get_value_ids)),
        ]


class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"
    _populate_dependencies = ["product.template"]

    def _populate(self, size):
        p_tmpl_ids = self.env.registry.populated_models["product.template"]
        ptavs = self.search([('product_tmpl_id', 'in', p_tmpl_ids)])
        # ptavs are automatically created when specifying attribute lines on product templates.

        rand = populate.Random("ptav_extra_price_generator")
        for ptav in ptavs:
            if rand.random() < 0.50:  # 50% of having a extra price
                ptav.price_extra = rand.randrange(500) * rand.random()

        return ptavs
