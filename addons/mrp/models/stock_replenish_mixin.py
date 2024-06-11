# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductReplenishMixin(models.AbstractModel):
    _inherit = 'stock.replenish.mixin'

    bom_id = fields.Many2one('mrp.bom', string="Bill of Material", compute='_compute_bom',
                             store=True, readonly=False, check_company=True)
    show_bom = fields.Boolean(compute='_compute_show_bom')

    @api.depends('product_id')
    def _compute_bom(self):
        for rec in self:
            rec.bom_id = self.env['mrp.bom']._bom_find(rec.product_id)[rec.product_id]

    @api.depends('route_id')
    def _compute_show_bom(self):
        for rec in self:
            rec.show_bom = rec._get_show_bom(rec.route_id)

    def _get_show_bom(self, route):
        return any(r.action == 'manufacture' for r in route.rule_ids)
