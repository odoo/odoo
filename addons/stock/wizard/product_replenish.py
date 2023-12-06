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
    date_planned = fields.Datetime('Scheduled Date', required=True, compute="_compute_date_planned", readonly=False,
        help="Date at which the replenishment should take place.", store=True, precompute=True)
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

    @api.depends('warehouse_id', 'product_id')
    def _compute_forecasted_quantity(self):
        for rec in self:
            rec.forecasted_quantity = rec.product_id.with_context(warehouse=rec.warehouse_id.id).virtual_available

    @api.depends('product_id', 'product_tmpl_id')
    def _compute_allowed_route_ids(self):
        domain = self._get_allowed_route_domain()
        route_ids = self.env['stock.route'].search(domain)
        self.allowed_route_ids = route_ids

    @api.depends('route_id')
    def _compute_date_planned(self):
        for rec in self:
            rec.date_planned = rec._get_date_planned(rec.route_id)

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
        if 'route_id' in fields and 'route_id' not in res and product_tmpl_id:
            res['route_id'] = self.env['stock.route'].search(self._get_route_domain(product_tmpl_id), limit=1).id
            if not res['route_id']:
                res['route_id'] = product_tmpl_id.route_ids.filtered(lambda r: r.company_id == self.env.company or not r.company_id)[0].id
        return res

    def _get_date_planned(self, route_id, **kwargs):
        now = fields.Datetime.now()
        delay = 0
        if route_id:
            delay = sum([rule.delay for rule in route_id.rule_ids])
        return fields.Datetime.add(now, days=delay)

    def launch_replenishment(self):
        if not self.route_id:
            raise UserError(_("You need to select a route to replenish your products"))
        uom_reference = self.product_id.uom_id
        self.quantity = self.product_uom_id._compute_quantity(self.quantity, uom_reference, rounding_method='HALF-UP')
        try:
            now = self.env.cr.now()
            self.env['procurement.group'].with_context(clean_context(self.env.context)).run([
                self.env['procurement.group'].Procurement(
                    self.product_id,
                    self.quantity,
                    uom_reference,
                    self.warehouse_id.lot_stock_id,  # Location
                    _("Manual Replenishment"),  # Name
                    _("Manual Replenishment"),  # Origin
                    self.warehouse_id.company_id,
                    self._prepare_run_values()  # Values
                )
            ])
            move = self._get_record_to_notify(now)
            notification = self._get_replenishment_order_notification(move)
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

    # TODO: to remove in master
    def _prepare_orderpoint_values(self):
        values = {
            'location_id': self.warehouse_id.lot_stock_id.id,
            'product_id': self.product_id.id,
            'qty_to_order': self.quantity,
        }
        if self.route_id:
            values['route_id'] = self.route_id.id
        return values

    def _prepare_run_values(self):
        replenishment = self.env['procurement.group'].create({})
        values = {
            'warehouse_id': self.warehouse_id,
            'route_ids': self.route_id,
            'date_planned': self.date_planned,
            'group_id': replenishment,
        }
        return values

    def _get_record_to_notify(self, date):
        return self.env['stock.move'].search([('write_date', '>=', date)], limit=1)

    def _get_replenishment_order_notification_link(self, move):
        if move.picking_id:
            action = self.env.ref('stock.stock_picking_action_picking_type')
            return [{
                'label': move.picking_id.name,
                'url': f'#action={action.id}&id={move.picking_id.id}&model=stock.picking&view_type=form'
            }]
        return False

    def _get_replenishment_order_notification(self, move):
        link = self._get_replenishment_order_notification_link(move)
        if not link:
            return False
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('The following replenishment order have been generated'),
                'message': '%s',
                'links': link,
                'sticky': False,
            }
        }

    # OVERWRITE in 'Drop Shipping', 'Dropship and Subcontracting Management' and 'Dropship and Subcontracting Management' to hide it
    def _get_allowed_route_domain(self):
        stock_location_inter_wh_id = self.env.ref('stock.stock_location_inter_wh').id
        return [
            ('product_selectable', '=', True),
            ('rule_ids.location_src_id', '!=', stock_location_inter_wh_id),
            ('rule_ids.location_dest_id', '!=', stock_location_inter_wh_id)
        ]

    def _get_route_domain(self, product_tmpl_id):
        company = product_tmpl_id.company_id or self.env.company
        domain = expression.AND([self._get_allowed_route_domain(), self.env['stock.route']._check_company_domain(company)])
        if product_tmpl_id.route_ids:
            domain = expression.AND([domain, [('product_ids', '=', product_tmpl_id.id)]])
        return domain
