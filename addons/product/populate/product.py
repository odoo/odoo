# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models
from odoo.tools import populate

_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    _inherit = "product.category"
    _populate_sizes = {"small": 50, "medium": 500, "large": 30000}

    def _populate_factories(self):
        def get_name(values=None, counter=0, complete=False, **kwargs):
            return "%s_%s_%s" % ("product_category", int(complete), counter)

        # quid of parent_id ???

        return [("name", populate.compute(get_name))]


class ProductProduct(models.Model):
    _inherit = "product.product"
    _populate_sizes = {"small": 150, "medium": 5000, "large": 60000}

    def _populate_factories(self):

        return [
            ("name", populate.constant('product_template_name_{counter}')),
            ("sequence", populate.randomize([False] + [i for i in range(1, 101)])),
            ("description", populate.constant('product_template_description_{counter}')),
            ("default_code", populate.constant('product_default_code_{counter}')),
            ("active", populate.randomize([True, False], [0.8, 0.2])),
        ]
