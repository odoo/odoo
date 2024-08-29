# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductReplenishMixin(models.AbstractModel):
    _inherit = 'stock.replenish.mixin'

    bom_id = fields.Many2one('mrp.bom', string="Bill of Material", check_company=True)
    show_bom = fields.Boolean(compute='_compute_show_bom')

    def default_get(self, fields):
        res = super().default_get(fields)
        if res.get('product_id'):
            product_id = self.env['product.product'].browse(res['product_id'])
            res['bom_id'] = self.env['mrp.bom']._bom_find(product_id)[product_id].id
        return res

    @api.depends('route_id')
    def _compute_show_bom(self):
        for rec in self:
            rec.show_bom = rec._get_show_bom(rec.route_id)

    def _get_show_bom(self, route):
        return any(r.action == 'manufacture' for r in route.rule_ids)
