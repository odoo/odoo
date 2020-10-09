# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import collections
from functools import reduce

from odoo import models
from odoo.tools import populate

_logger = logging.getLogger(__name__)


class ProductAttribute(models.Model):
    _inherit = "product.attribute"
    _populate_sizes = {"small": 20, "medium": 150, "large": 750}

    def _populate_factories(self):
        return [
            ("name", populate.constant('product_attribute{counter}')),
            ("sequence", populate.randomize([False] + [i for i in range(1, 101)])),
            ("create_variant", populate.randomize(["always", "dynamic", "no_variant"])),
        ]


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"
    _populate_dependencies = ["product.attribute"]
    _populate_sizes = {"small": 80, "medium": 1000, "large": 50000}

    def _populate_factories(self):
        attribute_ids = self.env.registry.populated_models["product.attribute"]

        return [
            ("name", populate.constant('product_attribute_value{counter}')),
            ("sequence", populate.randomize([False] + [i for i in range(1, 101)])),
            ("attribute_id", populate.randomize(attribute_ids)),
        ]


class ProductTemplate(models.Model):
    _inherit = "product.template"
    _populate_sizes = {"small": 150, "medium": 5000, "large": 60000}
    _populate_dependencies = ["product.attribute.value", "product.category"]

    def _populate_factories(self):
        category_ids = self.env.registry.populated_models["product.category"]
        types, types_distribution = self.env["product.product"]._populate_get_types()

        def get_rand_float(values, counter, random):
            return random.randrange(0, 1500) * random.random()

        # TODO random sale & purchase uoms
        product_factories = [
            ("name", populate.constant('product_template_name_{counter}')),
            ("sequence", populate.randomize([False] + [i for i in range(1, 101)])),
            ("description", populate.constant('product_template_description_{counter}')),
            ("default_code", populate.constant('product_default_code_{counter}')),
            ("active", populate.randomize([True, False], [0.8, 0.2])),
            ("type", populate.randomize(types, types_distribution)),
            ("categ_id", populate.randomize(category_ids)),
            ("lst_price", populate.compute(get_rand_float)),
            ("standard_price", populate.compute(get_rand_float)),
        ]

        # VFE TODO variants number limit check ???
        attribute_ids = self.env.registry.populated_models["product.attribute"]
        def get_attributes(values, counter, random):
            if not random.getrandbits(4):
                return False
            attributes_qty = random.choices(
                [1,2,3,4,5,6,8,10],
                [10,9,8,7,6,4,1,0.5],
            )[0]
            attr_line_vals = []
            values_count = []
            no_variant = False
            for j in range(attributes_qty):
                attr_id = random.choice(attribute_ids)
                attr = self.env["product.attribute"].browse(attr_id)
                if not attr.value_ids:
                    # attribute without any value
                    continue
                choices = [i for i in range(len(attr.value_ids))]
                vals_qty = random.choice(choices)
                value_ids = []
                for val in range(vals_qty+1):
                    random_value_id = attr.value_ids[random.choice(choices)].id
                    if random_value_id not in value_ids:
                        value_ids.append(random_value_id)

                attr_line_vals.append((0,0,{
                    "attribute_id": attr_id,
                    "value_ids": [(6,0,value_ids)],
                }))
                values_count+=[len(value_ids)]
                if attr.create_variant == "dynamic":
                    no_variant = True
            if not values_count:
                # Only attributes without values have been chosen.
                return attr_line_vals

            # Ensure that we wouldn't have > 1k variants with the generated attributes combination
            while not no_variant and reduce((lambda x, y: x * y), values_count) > 1000:
                attr_line_vals.pop()
                values_count.pop()
            return attr_line_vals

        return product_factories + [
            ("attribute_line_ids", populate.compute(get_attributes))
        ]


class ProductTemplateAttributeExclusion(models.Model):
    _inherit = "product.template.attribute.exclusion"
    _populate_dependencies = ["product.template"]
    _populate_sizes = {"small": 200, "medium": 1000, "large": 5000}

    def _populate(self, size):
        batch_size = 1000
        min_size = self._populate_sizes[size]
        rand = populate.Random("ptae_generator")
        create_values = []
        records_batches = []
        record_count = 0

        p_tmpl_ids = self.env.registry.populated_models["product.template"]
        configurable_templates = self.env["product.template"].search([
            ('id', 'in', p_tmpl_ids),
            ('has_configurable_attributes', '=', True),
        ])
        while record_count <= min_size:
            template = rand.choice(configurable_templates)
            multi_values_attribute_lines = template.attribute_line_ids.filtered(
                lambda l: len(l.value_ids) > 1
            )
            if len(multi_values_attribute_lines) < 2:
                continue
            first_line = rand.choice(multi_values_attribute_lines)
            ptav = rand.choice(first_line.product_template_value_ids)
            remaining_lines = multi_values_attribute_lines - first_line
            excluded_ptav = rand.choice(remaining_lines.product_template_value_ids)
            create_values.append({
                "product_template_attribute_value_id": ptav.id,
                "product_tmpl_id": template.id,
                "value_ids": [(6, 0, [excluded_ptav.id])],
            })
            record_count += 1
            if len(create_values) >= batch_size:
                _logger.info('Batch: %s/%s', record_count, min_size)
                records_batches.append(self.create(create_values))
                create_values = []

        if create_values:
            records_batches.append(self.create(create_values))
        return self.concat(*records_batches)


class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"
    _populate_dependencies = ["product.template"]

    def _populate(self, size):
        p_tmpl_ids = self.env.registry.populated_models["product.template"]
        ptavs = self.search([('product_tmpl_id', 'in', p_tmpl_ids)])
        # ptavs are automatically when specifying attribute lines on product templates.

        rand = populate.Random("ptav_extra_price_generator")
        for ptav in ptavs:
            if rand.getrandbits(1):
                ptav.price_extra = rand.randrange(0, 500) * rand.random()

        return ptavs
