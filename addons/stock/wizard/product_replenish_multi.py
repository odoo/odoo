# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tools.misc import clean_context
from odoo import api, fields, models, _


class ProductReplenishMultiLine(models.TransientModel):
    _name = 'product.replenish.multi.line'
    _description = 'Product Replenish Multi Line'

    wizard_id = fields.Many2one('product.replenish.multi', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade',
                                 domain=[('type', '=', 'product')])
    product_uom_category_id = fields.Many2one('uom.category', related='product_id.uom_id.category_id', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unity of measure', required=True)
    product_uom_qty = fields.Float('Quantity', default=1, required=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.ensure_one()
        self.product_uom_id = self.product_id.uom_id


class ProductReplenishMulti(models.TransientModel):
    _name = 'product.replenish.multi'
    _description = 'Product Replenish Multi'

    line_ids = fields.One2many('product.replenish.multi.line', 'wizard_id', string='Lines')
    warehouse_source_id = fields.Many2one('stock.warehouse', string='From')
    warehouse_id = fields.Many2one('stock.warehouse', string='To', required=True)
    date_planned = fields.Datetime('Scheduled Date', help="Date at which the replenishment should take place.")
    route_ids = fields.Many2many('stock.location.route', string='Preferred Routes',
                                 help="Apply specific route(s) for the replenishment instead of product's default routes.")

    def _set_route(self):
        route = self.env['stock.location.route'].search(
            [('supplied_wh_id', '=', self.warehouse_id.id),
             ('supplier_wh_id', '=', self.warehouse_source_id.id)],
            limit=1)
        if route:
            self.route_ids = route
        return route

    @api.onchange('warehouse_id', 'warehouse_source_id')
    def _onchange_warehouse(self):
        self.ensure_one()
        if self.warehouse_id and self.warehouse_source_id and self.warehouse_id != self.warehouse_source_id:
            route = self._set_route()
            if not route:
                self.warehouse_id.create_resupply_routes(self.warehouse_source_id)
                route = self._set_route()
                route.write({'product_categ_selectable': False,
                             'product_selectable': False,
                             'warehouse_selectable': False,
                             'sale_selectable': False,
                             'sequence': 1000})
                route.rule_ids.write({'partner_address_id': self.warehouse_id.partner_id.id})

    def launch_replenishment(self):
        self.ensure_one()
        if self.warehouse_id == self.warehouse_source_id:
            raise UserError(_('Same warehouse !'))
        values = self._prepare_run_values()
        for line in self.line_ids:
            uom_reference = line.product_id.uom_id
            quantity = line.product_uom_id._compute_quantity(line.product_uom_qty, uom_reference)
            try:
                self.env['procurement.group'].with_context(clean_context(self.env.context)).run(
                    line.product_id,
                    quantity,
                    uom_reference,
                    self.warehouse_id.lot_stock_id,  # Location
                    "Manual Replenishment",  # Name
                    "Manual Replenishment",  # Origin
                    values  # Values
                )
            except UserError as error:
                raise UserError(error)

    def _prepare_run_values(self):
        group = self.env['procurement.group'].create({})
        values = {
            'warehouse_id': self.warehouse_id,
            'route_ids': self.route_ids,
            'date_planned': self.date_planned or fields.Datetime.now(),
            'group_id': group,
        }
        return values
