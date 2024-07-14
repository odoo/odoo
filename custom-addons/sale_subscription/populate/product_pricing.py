# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate

from collections import defaultdict


class ProductPricing(models.Model):
    _inherit = 'product.pricing'
    _populate_sizes = {"small": 150, "medium": 5000, "large": 25000}
    _populate_dependencies = ['sale.temporal.recurrence', 'product.product']

    def _populate_factories(self):
        recurrence_id = self.env.registry.populated_models['sale.temporal.recurrence']
        product_template_id = self.env['product.product']\
            .browse(self.env.registry.populated_models['product.product'])\
            .product_tmpl_id.filtered('recurring_invoice').ids

        def get_rand_float(values, counter, random=None):
            return random.randrange(0, 1500) * random.random()

        def generate_template_values(iterator, field_name, model_name):
            random = populate.Random('templatevalues')
            counter = 0
            existing_pair = defaultdict(set)
            for values in iterator:
                template_id = random.choice(product_template_id)
                if template_id in existing_pair[values['recurrence_id']]:   # We filter out the existing pair
                    continue
                existing_pair[values['recurrence_id']].add(template_id)
                yield {**values, field_name: populate.format_str(template_id, counter, values)}
                counter += 1

        return [
            ('recurrence_id', populate.randomize(recurrence_id)),
            ('product_template_id', generate_template_values),
            ('price', populate.compute(get_rand_float))
        ]
