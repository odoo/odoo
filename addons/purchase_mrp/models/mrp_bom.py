# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_round


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
            for product in bom.product_tmpl_id.product_variant_ids:
                total_variant_cost_share = sum(bom.bom_line_ids.filtered(lambda bl: not bl._skip_bom_line(product) and not float_is_zero(bl.product_qty, precision_rounding=bl.product_uom_id.rounding)).mapped('cost_share'))
                if float_round(total_variant_cost_share, precision_digits=2) not in [0, 100]:
                    raise UserError(_("The total cost share for a BoM's component have to be 100"))
        return res

    @api.model
    def _round_last_line_done(self, lines_done):
        result = super()._round_last_line_done(lines_done)
        if result:
            result[-1][1]['line_cost_share'] = float_round(100.0 - sum(vals.get('line_cost_share', 0.0) for _, vals in result[:-1]), precision_digits=2)
        return result


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    cost_share = fields.Float(
        "Cost Share (%)", digits=(5, 2),  # decimal = 2 is important for rounding calculations!!
        help="The percentage of the component repartition cost when purchasing a kit."
             "The total of all components' cost have to be equal to 100.")

    def _get_cost_share(self):
        self.ensure_one()
        product = self.env.context.get('bom_variant_id', self.env['product.product'])
        variant_bom_lines = self.bom_id.bom_line_ids.filtered(lambda bl: not bl._skip_bom_line(product) and not float_is_zero(bl.product_qty, precision_rounding=bl.product_uom_id.rounding))
        if not float_is_zero(self.cost_share, precision_digits=2) or not len(variant_bom_lines) or not all(float_is_zero(bom_line.cost_share, precision_digits=2) for bom_line in variant_bom_lines):
            return self.cost_share / 100
        return 1 / len(variant_bom_lines)

    def _prepare_bom_done_values(self, quantity, product, original_quantity, boms_done):
        result = super()._prepare_bom_done_values(quantity, product, original_quantity, boms_done)
        result['bom_cost_share'] = self._get_line_cost_share(product, boms_done)
        return result

    def _prepare_line_done_values(self, quantity, product, original_quantity, parent_line, boms_done):
        result = super()._prepare_line_done_values(quantity, product, original_quantity, parent_line, boms_done)
        result['line_cost_share'] = float_round(self._get_line_cost_share(product, boms_done), precision_digits=2)
        return result

    def _get_line_cost_share(self, product, boms_done):
        if not self:
            return 100.0
        self.ensure_one()
        parent_cost_share = next((vals.get('bom_cost_share', 100.0) for bom, vals in reversed(boms_done) if bom == self.bom_id), 100)
        line_cost_share = parent_cost_share * self.with_context(bom_variant_id=product)._get_cost_share()
        return line_cost_share
