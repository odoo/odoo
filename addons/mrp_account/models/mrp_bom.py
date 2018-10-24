# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    cost_repartition = fields.Float('Cost Repartition for final product',
        default=100.0, digits='Product Unit of Measure',
        required=True, help="Percentage of the total cost of the components\
        that should be attributed to the finished product produced.")

    total_cost_repartition = fields.Float('Total percentage of cost repartition\
        (should be 100)', digits='Product Unit of Measure',
        compute='compute_total_cost_repartition')

    @api.depends('bom_line_ids.cost_repartition', 'byproduct_ids.cost_repartition', 'cost_repartition')
    def compute_total_cost_repartition(self):
        """ Compute total_cost_repartition for the current BoM. It's used to
        display a warning to the user if the repartition is different than 100%.
        """
        if self.type == 'phantom':
            self.total_cost_repartition = sum(self.bom_line_ids.mapped('cost_repartition'))
        else:
            self.total_cost_repartition = self.cost_repartition + sum(self.byproduct_ids.mapped('cost_repartition'))


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    cost_repartition = fields.Float('Cost Repartition', default=0.0,
        digits='Product Unit of Measure')

class MrpByProduct(models.Model):
    _inherit = 'mrp.bom.byproduct'

    cost_repartition = fields.Float('Cost Repartition', default=0.0,
        digits='Product Unit of Measure')
