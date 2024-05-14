# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _populate_factories(self):
        def get_is_storable(values, counter, random):
            if values["type"] == "consu":
                return random.choices([True, False], [0.8, 0.2])[0]
            return False

        def get_tracking(values, counter, random):
            if values['is_storable']:
                return random.choices(['none', 'lot', 'serial'], [0.7, 0.2, 0.1])[0]
            return 'none'

        return super()._populate_factories() + [
            ('is_storable', populate.compute(get_is_storable)),
            ('tracking', populate.compute(get_tracking))
        ]
