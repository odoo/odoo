# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductReplenishMixin(models.AbstractModel):
    _inherit = 'stock.replenish.mixin'

    supplier_id = fields.Many2one('product.supplierinfo', string="Vendor", check_company=True)
    show_vendor = fields.Boolean(compute='_compute_show_vendor')

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if res.get('product_id'):
            product_id = self.env['product.product'].browse(res['product_id'])
            product_tmpl_id = product_id.product_tmpl_id
            company = product_tmpl_id.company_id or self.env.company
            if 'warehouse_id' not in res:
                res['warehouse_id'] = self.env['stock.warehouse'].search([
                    *self.env['stock.warehouse']._check_company_domain(company),
                ], limit=1).id
            orderpoint = self.env['stock.warehouse.orderpoint'].search(
                [('product_id', 'in', [product_tmpl_id.product_variant_id.id, product_id.id]),
                 ("warehouse_id", "=", res['warehouse_id'])], limit=1)
            res['supplier_id'] = False
            if orderpoint:
                res['supplier_id'] = orderpoint.supplier_id.id
            elif product_tmpl_id.seller_ids:
                res['supplier_id'] = product_tmpl_id.seller_ids[0].id
        return res

    # @api.depends('product_id', 'route_id')
    # def _compute_supplier(self):
    #     for rec in self:
    #         rec.supplier_id = rec.product_id.seller_ids[:1] if rec.show_vendor else False

    @api.depends('route_id')
    def _compute_show_vendor(self):
        for rec in self:
            rec.show_vendor = rec._get_show_vendor(rec.route_id)

    def _get_show_vendor(self, route):
        return any(r.action == 'buy' for r in route.rule_ids)
