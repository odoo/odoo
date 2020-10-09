# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import collections

from odoo import models
from odoo.tools import populate

_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    _inherit = "product.category"
    _populate_sizes = {"small": 50, "medium": 500, "large": 30000}

    def _populate_factories(self):
        def get_name(values=None, counter=0, complete=False, **kwargs):
            return "%s_%s_%s" % ("product_category", int(complete), counter)

        return [("name", populate.compute(get_name))]

    def _populate(self, size):
        categories = super()._populate(size)
        # set parent_ids
        self._populate_set_parents(categories, size)
        return categories

    def _populate_set_parents(self, categories, size):
        _logger.info('Setting parent categories')
        parents = self.env["product.category"]
        rand = populate.Random('product.product+parent_generator')
        for category in categories:
            if not rand.getrandbits(4):
                parents |= category
        parent_ids = parents.ids
        categories -= parents # Avoid recursion in parent-child relations.
        parent_childs = collections.defaultdict(lambda: self.env['product.category'])
        for count, category in enumerate(categories):
            if not rand.getrandbits(2): # 1/4 of remaining categories have a parent.
                parent_childs[rand.choice(parent_ids)] |= category

        for count, (parent, children) in enumerate(parent_childs.items()):
            if (count + 1) % 100 == 0:
                _logger.info('Setting parent: %s/%s', count + 1, len(parents))
            children.write({'parent_id': parent})

class ProductProduct(models.Model):
    _inherit = "product.product"
    _populate_sizes = {"small": 150, "medium": 5000, "large": 60000}
    _populate_dependencies = ["product.category"]

    def _populate_get_types(self):
        return ["consu", "service"], [2, 1]

    def _populate_factories(self):
        category_ids = self.env.registry.populated_models["product.category"]
        types, types_distribution = self._populate_get_types()

        def get_rand_float(values, counter, random):
            return random.randrange(0, 1500) * random.random()

        return [
            ("name", populate.constant('product_product_name_{counter}')),
            ("sequence", populate.randomize([False] + [i for i in range(1, 101)])),
            ("description", populate.constant('product_template_description_{counter}')),
            ("default_code", populate.constant('product_default_code_{counter}')),
            ("active", populate.randomize([True, False], [0.8, 0.2])),
            ("type", populate.randomize(types, types_distribution)),
            ("categ_id", populate.randomize(category_ids)),
            ("lst_price", populate.compute(get_rand_float)),
            ("standard_price", populate.compute(get_rand_float)),
        ]
