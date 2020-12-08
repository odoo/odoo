# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv.expression import OR


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_view_stock_valuation_layers(self):
        action = super(StockPicking, self).action_view_stock_valuation_layers()
        subcontracted_productions = self._get_subcontracted_productions()
        if not subcontracted_productions:
            return action
        domain = action['domain']
        domain_subcontracting = [('id', 'in', (subcontracted_productions.move_raw_ids | subcontracted_productions.move_finished_ids).stock_valuation_layer_ids.ids)]
        domain = OR([domain, domain_subcontracting])
        return dict(action, domain=domain)

    def _prepare_subcontract_mo_vals(self, subcontract_move, bom):
        vals = super(StockPicking, self)._prepare_subcontract_mo_vals(subcontract_move, bom)
        if bom.product_tmpl_id.cost_method in ('fifo', 'average'):
            vals = dict(vals, extra_cost=subcontract_move._get_price_unit())
        return vals


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_common_svl_vals(self):
        # if we are subcontracting we want to have the receipt move
        # on the svl, not the MO
        vals = super()._prepare_common_svl_vals()
        if self.move_dest_ids and self.move_dest_ids[0].is_subcontract:
            vals['stock_move_id'] = self.move_dest_ids[0].id
        return vals
