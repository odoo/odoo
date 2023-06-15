# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.misc import clean_context


class ProductReplenish(models.TransientModel):
    _name = 'product.replenish'
    _description = 'Product Replenish'
    _check_company_auto = True

    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', required=True)
    product_has_variants = fields.Boolean('Has variants', default=False, required=True)
    product_uom_category_id = fields.Many2one('uom.category', related='product_id.uom_id.category_id', readonly=True, required=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unity of measure', required=True)
    forecast_uom_id = fields.Many2one(related='product_id.uom_id')
    quantity = fields.Float('Quantity', default=1, required=True)
    date_planned = fields.Datetime('Scheduled Date', required=True, help="Date at which the replenishment should take place.")
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', required=True,
        check_company=True,
    )
    route_id = fields.Many2one(
        'stock.route', string='Preferred Route',
        help="Apply specific route for the replenishment instead of product's default routes.",
        check_company=True,
    )
    company_id = fields.Many2one('res.company')
    forecasted_quantity = fields.Float(string="Forecasted Quantity", compute="_compute_forecasted_quantity")
    allowed_route_ids = fields.Many2many("stock.route", compute="_compute_allowed_route_ids")

    @api.onchange('product_id', 'warehouse_id')
    def _onchange_product_id(self):
        if not self.env.context.get('default_quantity'):
            self.quantity = abs(self.forecasted_quantity) if self.forecasted_quantity < 0 else 1

    @api.model
    def default_get(self, fields):
        res = super(ProductReplenish, self).default_get(fields)
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
        company = product_tmpl_id.company_id or self.env.company
        if 'product_uom_id' in fields:
            res['product_uom_id'] = product_tmpl_id.uom_id.id
        if 'company_id' in fields:
            res['company_id'] = company.id
        if 'warehouse_id' in fields and 'warehouse_id' not in res:
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
            res['warehouse_id'] = warehouse.id
        if 'date_planned' in fields:
            res['date_planned'] = datetime.datetime.now()
        if 'route_id' in fields and 'route_id' not in res:
            route_id = False
            domain = expression.AND([self._get_allowed_route_domain(), ['|', ('company_id', '=', False), ('company_id', '=', company.id)]])
            if product_tmpl_id.route_ids:
                product_route_domain = expression.AND([domain, [('product_ids', '=', product_tmpl_id.id)]])
                route_id = self.env['stock.route'].search(product_route_domain, limit=1).id
            if not route_id:
                route_id = self.env['stock.route'].search(domain, limit=1).id
            if route_id:
                res['route_id'] = route_id
        return res

    def launch_replenishment(self):
        uom_reference = self.product_id.uom_id
        self.quantity = self.product_uom_id._compute_quantity(self.quantity, uom_reference, rounding_method='HALF-UP')
        try:
            orderpoint = self.env['stock.warehouse.orderpoint'].search([('product_id', '=', self.product_id.id)])
            if orderpoint:
                orderpoint.write(self._prepare_orderpoint_values())
            else:
                orderpoint = self.env['stock.warehouse.orderpoint'].create(self._prepare_orderpoint_values())
            notification = orderpoint.action_replenish()
            act_window_close = {
                'type': 'ir.actions.act_window_close',
                'infos': {'done': True},
            }
            if notification:
                notification['params']['next'] = act_window_close
                return notification
            return act_window_close
        except UserError as error:
            raise UserError(error)

    def _prepare_orderpoint_values(self):
        values = {
            'location_id': self.warehouse_id.lot_stock_id.id,
            'product_id': self.product_id.id,
            'qty_to_order': self.quantity,
        }
        if self.route_id:
            values['route_id'] = self.route_id.id
        return values

    @api.depends('warehouse_id', 'product_id')
    def _compute_forecasted_quantity(self):
        for rec in self:
            rec.forecasted_quantity = rec.product_id.with_context(warehouse=rec.warehouse_id.id).virtual_available

    # OVERWRITE in 'Drop Shipping', 'Dropship and Subcontracting Management' and 'Dropship and Subcontracting Management' to hide it
    def _get_allowed_route_domain(self):
        stock_location_inter_wh_id = self.env.ref('stock.stock_location_inter_wh').id
        return [
            ('product_selectable', '=', True),
            ('rule_ids.location_src_id', '!=', stock_location_inter_wh_id),
            ('rule_ids.location_dest_id', '!=', stock_location_inter_wh_id)
        ]

    @api.depends('product_id', 'product_tmpl_id')
    def _compute_allowed_route_ids(self):
        domain = self._get_allowed_route_domain()
        route_ids = self.env['stock.route'].search(domain)
        self.allowed_route_ids = route_ids
