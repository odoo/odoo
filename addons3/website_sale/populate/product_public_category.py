# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import logging

from odoo import models
from odoo.fields import Command
from odoo.tools import populate

_logger = logging.getLogger(__name__)


class ProductPublicCategory(models.Model):
    _inherit = 'product.public.category'
    _populate_sizes = {'small': 20, 'medium': 100, 'large': 1_500}
    _populate_dependencies = ['product.template']

    def _populate_factories(self):

        p_tmpl_ids = self.env.registry.populated_models['product.template']
        max_products_in_category = min(len(p_tmpl_ids), 500)
        def get_products(iterator, field_name, model_name):
            random = populate.Random('product_public_category_products')
            for values in iterator:
                # Fixed price, percentage, formula
                number_of_products = random.randint(1, max_products_in_category)
                product_tmpl_ids = set()
                for _i in range(number_of_products):
                    product_tmpl_ids.add(
                        random.choice(p_tmpl_ids)
                    )
                values['product_tmpl_ids'] = [Command.set(product_tmpl_ids)]
                yield values

        return [
            ('name', populate.constant('PC_{counter}')),
            ('sequence', populate.randomize([False] + [i for i in range(1, 101)])),
            ('_products', get_products),
        ]

    def _populate(self, size):
        categories = super()._populate(size)
        # Set parent/child relation
        self._populate_set_parents(categories, size)
        return categories

    def _populate_set_parents(self, categories, size):
        _logger.info('Set parent/child relation of product categories')
        parent_ids = []
        rand = populate.Random('product.public.category+parent_generator')

        for category in categories:
            if rand.random() < 0.25:
                parent_ids.append(category.id)

        categories -= self.browse(parent_ids)  # Avoid recursion in parent-child relations.
        parent_childs = defaultdict(lambda: self.env['product.public.category'])
        for category in categories:
            if rand.random() < 0.25:  # 1/4 of remaining categories have a parent.
                parent_childs[rand.choice(parent_ids)] |= category

        for count, (parent, children) in enumerate(parent_childs.items()):
            if (count + 1) % 1000 == 0:
                _logger.info('Setting parent: %s/%s', count + 1, len(parent_childs))
            children.write({'parent_id': parent})
