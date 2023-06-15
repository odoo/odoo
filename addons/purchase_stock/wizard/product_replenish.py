# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.osv.expression import AND


class ProductReplenish(models.TransientModel):
    _inherit = 'product.replenish'

    supplier_id = fields.Many2one("product.supplierinfo", string="Vendor")
    show_vendor = fields.Boolean(compute="_compute_show_vendor")

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
            orderpoint = self.env['stock.warehouse.orderpoint'].search([('product_id', 'in', [product_tmpl_id.product_variant_id.id, product_id.id]), ("warehouse_id", "=", res['warehouse_id'])], limit=1)
            if orderpoint:
                res['supplier_id'] = orderpoint.supplier_id.id
            elif product_tmpl_id.seller_ids:
                res['supplier_id'] = product_tmpl_id.seller_ids[0].id
            if not product_tmpl_id.seller_ids:
                domain = self.env['stock.route']._check_company_domain(company) + self._get_allowed_route_domain()
                domain = AND([domain, [('id', '!=', self.env.ref('purchase_stock.route_warehouse0_buy', raise_if_not_found=False).id)]])
                res['route_id'] = self.env['stock.route'].search(domain, limit=1).id
        return res

    @api.depends('route_id')
    def _compute_show_vendor(self):
        for rec in self:
            rec.show_vendor = rec.route_id == self.env.ref('purchase_stock.route_warehouse0_buy', raise_if_not_found=False)

    @api.onchange('route_id')
    def _onchange_route_id(self):
        for rec in self:
            if rec.route_id == self.env.ref('purchase_stock.route_warehouse0_buy', raise_if_not_found=False) and not rec.product_id.product_tmpl_id.seller_ids:
                return {
                    'warning': {
                        'title': _("Vendor Not Found in Product %s", rec.product_id.name),
                        'message': _("Go on the product form and add the list of vendors"),
                    },
                }

    def _prepare_orderpoint_values(self):
        res = super()._prepare_orderpoint_values()
        if self.supplier_id:
            res['supplier_id'] = self.supplier_id.id
        return res

    def action_stock_replenishment_info(self):
        self.ensure_one()
        orderpoint = self.env["stock.warehouse.orderpoint"].search([("product_id", "=", self.product_id.id), ("warehouse_id", "=", self.warehouse_id.id)], limit=1)
        if not orderpoint:
            orderpoint = self.env["stock.warehouse.orderpoint"].create({
                "product_id": self.product_id.id,
                "warehouse_id": self.warehouse_id.id,
            })
        action = orderpoint.action_stock_replenishment_info()

        action["context"] = {
            'default_orderpoint_id': orderpoint.id,
            'replenish_id': self.id,
        }
        return action
