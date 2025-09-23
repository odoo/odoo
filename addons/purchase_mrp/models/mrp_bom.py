# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    @api.constrains('product_id', 'product_tmpl_id', 'bom_line_ids', 'byproduct_ids', 'operation_ids')
    def _check_bom_lines(self):
        res = super()._check_bom_lines()
        for bom in self:
            if all(not bl.cost_share for bl in bom.bom_line_ids):
                continue
            if any(bl.cost_share < 0 for bl in bom.bom_line_ids):
                raise UserError(_("Components cost share have to be positive or equals to zero."))
            if float_compare(sum(bom.bom_line_ids.mapped('cost_share')), 100, precision_digits=2) != 0:
                raise UserError(_("The total cost share for a BoM's component have to be 100"))
        return res

    def explode(self, product, quantity, picking_type=False, never_attribute_values=False):
        boms_done, lines_done = super().explode(product, quantity, picking_type, never_attribute_values)
        total_cumul = 0.0

        # Don't use cumulative cost share for single level BoM to avoid rounding issues
        if not any(line_done[1]['parent_line'] for line_done in lines_done):
            return boms_done, lines_done

        for bom_line, line_done in lines_done:
            cumul_cost_share = bom_line._get_cost_share()
            parent_line = line_done['parent_line']
            while parent_line:
                cumul_cost_share *= parent_line._get_cost_share()
                for bom_done in boms_done:
                    bom_data = bom_done[1]
                    if bom_data['parent_line'] == parent_line:
                        parent_line = bom_data['real_parent_line']
                        break
            if line_done is lines_done[-1][1]:
                cumul_cost_share = (1.0 - total_cumul)
            cumul_cost_share = float_round(cumul_cost_share, precision_digits=2)
            total_cumul += cumul_cost_share
            line_done['cost_share'] = cumul_cost_share

        return boms_done, lines_done


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    cost_share = fields.Float(
        "Cost Share (%)", digits=(5, 2),  # decimal = 2 is important for rounding calculations!!
        help="The percentage of the component repartition cost when purchasing a kit."
             "The total of all components' cost have to be equal to 100.")

    def _get_cost_share(self):
        self.ensure_one()
        if self.cost_share or any(bom_line.cost_share != 0.0 for bom_line in self.bom_id.bom_line_ids):
            return self.cost_share / 100
        bom = self.bom_id
        bom_lines_without_cost_share = bom.bom_line_ids.filtered(lambda bl: not bl.cost_share)
        return 1 / len(bom_lines_without_cost_share)
