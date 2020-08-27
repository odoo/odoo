# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import models
from odoo.tools import populate

_logger = logging.getLogger(__name__)

class ProductProduct(models.Model):
    _inherit = "product.product"

    def _populate_factories(self):
        result = super(ProductProduct, self)._populate_factories()
        result.append(("website_published", populate.constant(True)))
        return result
