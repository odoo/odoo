# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_mo_vals(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values, bom):
        res = super()._prepare_mo_vals(product_id, product_qty, product_uom, location_id, name, origin, company_id, values, bom)
        if values.get('project_id'):
            res['project_id'] = values.get('project_id')
        return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_procurement_values(self):
        res = super()._prepare_procurement_values()
        if res.get('group_id') and len(res['group_id'].mrp_production_ids) == 1:
            res['project_id'] = res['group_id'].mrp_production_ids.project_id.id
        return res

    @api.depends('production_id.project_id')
    def _compute_project_id(self):
        super()._compute_project_id()
        for move in self:
            if move.production_id:
                move.project_id = move.production_id.project_id
