# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    _populate_dependencies = ['stock.rule']

    def _populate_factories(self):
        def get_subcontracting_dropshipping_pull_id(values, counter, random):
            return random.choice(self.env['stock.rule'].search([])).id

        return super()._populate_factories() + [
            ('subcontracting_dropshipping_to_resupply', populate.iterate([True, False])),
            ('subcontracting_dropshipping_pull_id', get_subcontracting_dropshipping_pull_id)
        ]
