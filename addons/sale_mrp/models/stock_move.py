# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.depends('bom_line_id')
    def _compute_packaging_uom_id(self):
        super()._compute_packaging_uom_id()
        for move in self:
            if move.bom_line_id and move.bom_line_id.bom_id.type == 'phantom':
                move.packaging_uom_id = move.uom_id

    def _get_source_document(self):
        return self.production_id or self.raw_material_production_id or super()._get_source_document()

    def _prepare_procurement_values(self):
        res = super()._prepare_procurement_values()
        distribution = self.raw_material_production_id.sale_line_id.analytic_distribution
        if distribution and not res.get('analytic_distribution'):
            res['analytic_distribution'] = distribution
        return res
