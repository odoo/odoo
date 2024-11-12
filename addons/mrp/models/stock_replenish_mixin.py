# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockReplenishMixin(models.AbstractModel):
    _inherit = 'stock.replenish.mixin'

    bom_id = fields.Many2one('mrp.bom', string="Bill of Material")
    show_bom = fields.Boolean(compute='_compute_show_bom')

    @api.depends('route_id')
    def _compute_show_bom(self):
        for rec in self:
            rec.show_bom = rec._get_show_bom(rec.route_id)

    def _get_show_bom(self, route):
        return any(r.action == 'manufacture' for r in route.rule_ids)
