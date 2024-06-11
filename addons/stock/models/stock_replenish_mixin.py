# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductReplenishMixin(models.AbstractModel):
    _name = 'stock.replenish.mixin'
    _description = 'Product Replenish Mixin'

    route_id = fields.Many2one('stock.route', string="Preferred Route", compute='_compute_route',
                               store=True, readonly=False, check_company=True)
    allowed_route_ids = fields.Many2many('stock.route', compute='_compute_allowed_route_ids')

    @api.depends('product_id', 'product_id.route_ids')
    def _compute_route(self):
        for rec in self:
            rec.route_id = next((r for r in rec.product_id.route_ids if r.id in rec.allowed_route_ids.ids), False)

    # INHERITS in 'Drop Shipping', 'Dropship and Subcontracting Management' and 'Dropship and Subcontracting Management'
    @api.depends('product_id', 'product_tmpl_id')
    def _compute_allowed_route_ids(self):
        domain = self._get_allowed_route_domain()
        route_ids = self.env['stock.route'].search(domain)
        self.allowed_route_ids = route_ids

    # TODO: remove dynamic domain
    # OVERWRITE in 'Drop Shipping', 'Dropship and Subcontracting Management' and 'Dropship and Subcontracting Management' to hide it
    def _get_allowed_route_domain(self):
        stock_location_inter_company_id = self.env.ref('stock.stock_location_inter_company').id
        return [
            ('product_selectable', '=', True),
            ('rule_ids.location_src_id', '!=', stock_location_inter_company_id),
            ('rule_ids.location_dest_id', '!=', stock_location_inter_company_id)
        ]
