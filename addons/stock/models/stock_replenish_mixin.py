# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class ProductReplenishMixin(models.AbstractModel):
    _name = 'stock.replenish.mixin'
    _description = 'Product Replenish Mixin'

    route_id = fields.Many2one('stock.route', string="Preferred Route", check_company=True)
    allowed_route_ids = fields.Many2many('stock.route', compute='_compute_allowed_route_ids')

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        product_tmpl_id = self.env['product.template']
        if self.env.context.get('default_product_id'):
            product_id = self.env['product.product'].browse(self.env.context['default_product_id'])
            product_tmpl_id = product_id.product_tmpl_id
            if 'product_id' in fields:
                res['product_tmpl_id'] = product_id.product_tmpl_id.id
                res['product_id'] = product_id.id
        elif self.env.context.get('default_product_tmpl_id'):
            product_tmpl_id = self.env['product.template'].browse(self.env.context['default_product_tmpl_id'])
            if 'product_id' in fields:
                res['product_tmpl_id'] = product_tmpl_id.id
                res['product_id'] = product_tmpl_id.product_variant_id.id
                if len(product_tmpl_id.product_variant_ids) > 1:
                    res['product_has_variants'] = True
        if 'route_id' in fields and 'route_id' not in res and product_tmpl_id:
            res['route_id'] = self.env['stock.route'].search(self._get_route_domain(product_tmpl_id), limit=1).id
            if not res['route_id']:
                if product_tmpl_id.route_ids:
                    res['route_id'] = product_tmpl_id.route_ids.filtered(lambda r: r.company_id == self.env.company or not r.company_id)[0].id
        return res

    def _get_route_domain(self, product_tmpl_id):
        company = product_tmpl_id.company_id or self.env.company
        domain = expression.AND([self._get_allowed_route_domain(), self.env['stock.route']._check_company_domain(company)])
        domain = expression.AND([domain, [('id', 'not in', self.env['stock.warehouse'].search([]).crossdock_route_id.ids)]])
        if product_tmpl_id.route_ids:
            domain = expression.AND([domain, [('product_ids', '=', product_tmpl_id.id)]])
        return domain

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
