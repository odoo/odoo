# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain


class StockReplenishMixin(models.AbstractModel):
    _name = 'stock.replenish.mixin'
    _description = 'Product Replenish Mixin'

    route_id = fields.Many2one(
        'stock.route', string="Preferred Route",
        help="Apply specific route for the replenishment instead of product's default routes.",
        check_company=True)
    allowed_route_ids = fields.Many2many('stock.route', compute='_compute_allowed_route_ids')

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

        base_domain = Domain('product_selectable', '=', True)
        if self.warehouse_id:
            wh_route_ids = self.warehouse_id.route_ids.filtered(lambda r: r._is_valid_resupply_route_for_product(self.product_id)).ids
            if wh_route_ids:
                base_domain |= Domain('id', 'in', wh_route_ids)

        return Domain.AND([
            base_domain,
            Domain('rule_ids.location_src_id', '!=', stock_location_inter_company_id),
            Domain('rule_ids.location_dest_id', '!=', stock_location_inter_company_id),
            Domain('rule_ids.location_dest_id.warehouse_id', '!=', False),
        ])
