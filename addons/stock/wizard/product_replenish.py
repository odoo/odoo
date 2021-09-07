# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import clean_context


class ProductReplenish(models.TransientModel):
    _name = 'product.replenish'
    _description = 'Product Replenish'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_tmpl_id = fields.Many2one('product.template', string='Product Template', required=True)
    product_has_variants = fields.Boolean('Has variants', default=False, required=True)
    product_uom_category_id = fields.Many2one('uom.category', related='product_id.uom_id.category_id', readonly=True, required=True)
    product_uom_id = fields.Many2one('uom.uom', related='product_id.uom_id')
    uom_id = fields.Many2one('uom.uom', string='Unity of measure', required=True)
    quantity = fields.Float('Quantity', default=1, required=True)
    date_planned = fields.Datetime('Scheduled Date', required=True, help="Date at which the replenishment should take place.")
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse', required=True,
        domain="[('company_id', '=', company_id)]")
    route_id = fields.Many2one(
        'stock.location.route', string='Preferred Route',
        help="Apply specific route for the replenishment instead of product's default routes.",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    company_id = fields.Many2one('res.company')
    forecasted_quantity = fields.Float(string="Forecasted Quantity", compute="_compute_forecasted_quantity")
    allowed_route_ids = fields.Many2many("stock.location.route", compute="_compute_allowed_route_ids")
    show_vendor = fields.Boolean(compute="_compute_show_vendor")

    @api.model
    def default_get(self, fields):
        res = super(ProductReplenish, self).default_get(fields)
        product_tmpl_id = self.env['product.template']
        if 'product_id' in fields:
            if self.env.context.get('default_product_id'):
                product_id = self.env['product.product'].browse(self.env.context['default_product_id'])
                product_tmpl_id = product_id.product_tmpl_id
                res['product_tmpl_id'] = product_id.product_tmpl_id.id
                res['product_id'] = product_id.id
            elif self.env.context.get('default_product_tmpl_id'):
                product_tmpl_id = self.env['product.template'].browse(self.env.context['default_product_tmpl_id'])
                res['product_tmpl_id'] = product_tmpl_id.id
                res['product_id'] = product_tmpl_id.product_variant_id.id
                if len(product_tmpl_id.product_variant_ids) > 1:
                    res['product_has_variants'] = True
        company = product_tmpl_id.company_id or self.env.company
        if 'uom_id' in fields:
            res['uom_id'] = product_tmpl_id.uom_id.id
        if 'company_id' in fields:
            res['company_id'] = company.id
        if 'warehouse_id' in fields and 'warehouse_id' not in res:
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
            res['warehouse_id'] = warehouse.id
        if 'date_planned' in fields:
            res['date_planned'] = datetime.datetime.now()
        return res

    def launch_replenishment(self):
        uom_reference = self.product_id.uom_id
        self.quantity = self.product_uom_id._compute_quantity(self.quantity, uom_reference)
        try:
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
        except UserError as error:
            raise UserError(error)

    def _prepare_run_values(self):
        replenishment = self.env['procurement.group'].create({})

        values = {
            'warehouse_id': self.warehouse_id,
            'route_ids': self.route_id,
            'date_planned': self.date_planned,
            'group_id': replenishment,
        }
        return values

    @api.depends('warehouse_id', 'product_id')
    def _compute_forecasted_quantity(self):
        self.forecasted_quantity = self.product_id.with_context(warehouse=self.warehouse_id.id).virtual_available

    @api.depends('route_id')
    def _compute_show_vendor(self):
        for rec in self:
            rec.show_vendor = rec.route_id.name == "Buy"

    @api.depends('product_id', 'product_tmpl_id')
    def _compute_allowed_route_ids(self):
        route_ids = self.env['stock.rule'].search([('picking_type_id.active', '=', True), ('picking_type_id.sequence_code', '!=', 'DS'), ('company_id', '=?', self.company_id.id)]).route_id.ids
        for rec in self:
            rec.allowed_route_ids = list(set(route_ids).intersection(rec.product_id.route_ids.ids))

    @api.onchange('route_id')
    def _onchange_route_id(self):
        for rec in self:
            if rec.route_id.name == (_("Buy")) and not rec.product_id.product_tmpl_id.seller_ids:
                raise UserError(_("No vendor list defined for product %s. Go on the product form and complete the list of vendors.", rec.product_id.name))

    def action_stock_replenishment_info(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('stock.action_stock_replenishment_info')
        orderpoint = self.env["stock.warehouse.orderpoint"].search([("product_id", "=", self.product_id.id)])
        if not orderpoint:
            orderpoint = self.env["stock.warehouse.orderpoint"].create({
                "product_id": self.product_id.id,
                "warehouse_id": self.warehouse_id.id,
            })
        action["context"] = {"default_orderpoint_id": orderpoint.id}
        return action
