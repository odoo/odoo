# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random

from odoo import models

class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def _populate(self, size):
        landed_costs = super()._populate(size)
        random.sample(landed_costs, random.randint(0, len(landed_costs) // 2)).write({'target_model': 'manufacturing'})
        return landed_costs
