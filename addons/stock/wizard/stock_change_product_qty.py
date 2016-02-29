# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError, AccessError


class StockChangeProductQty(models.TransientModel):
    _name = "stock.change.product.qty"
    _description = "Change Product Quantity"

    product_id = fields.Many2one('product.product', string='Product', required=True, default=lambda self: self.env.context.get('active_id', False))
    product_tmpl_id = fields.Many2one('product.template', string='Template', required=True)
    product_variant_count = fields.Integer(related='product_tmpl_id.product_variant_count', string='Variant Number')
    new_quantity = fields.Float(string='New Quantity on Hand',
        digits_compute=dp.get_precision('Product Unit of Measure'), required=True,
        help='This quantity is expressed in the Default Unit of Measure of the product.', default=1)
    lot_id = fields.Many2one('stock.production.lot', string='Serial Number', domain="[('product_id', '=', product_id)]")
    location_id = fields.Many2one('stock.location', string='Location', required=True, domain="[('usage', '=', 'internal')]")

    @api.model
    def default_get(self, fields):
        res = super(StockChangeProductQty, self).default_get(fields)

        if self.env.context.get('active_model') == 'product.template':
            product = self.env['product.product'].search([('product_tmpl_id', '=', self.env.context.get('active_id'))], limit=1)
            if product:
                res['product_id'] = product.id

        if 'location_id' in fields:
            location_id = res.get('location_id', False)
            if not location_id:
                try:
                    location_id = self.env.ref('stock.stock_location_stock')
                except (AccessError):
                    pass
            if location_id:
                try:
                    location_id.check_access_rule('read')
                except (AccessError):
                    location_id = False
            res['location_id'] = location_id
        return res

    @api.model
    def create(self, values):
        if values.get('product_id'):
            stock_change_product_qty = self.new({'product_id': values['product_id']})
            stock_change_product_qty._onchange_product_id()
            values.update(stock_change_product_qty._convert_to_write(stock_change_product_qty._cache))
        return super(StockChangeProductQty, self).create(values)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.product_tmpl_id = self.product_id.product_tmpl_id
        self.product_variant_count = self.product_id.product_tmpl_id.product_variant_count

    @api.multi
    def change_product_qty(self):
        """ Changes the Product Quantity by making a Physical Inventory. """

        Inventory = self.env['stock.inventory']
        InventoryLine = self.env['stock.inventory.line']

        for data in self:
            if data.new_quantity < 0:
                raise UserError(_('Quantity cannot be negative.'))
            ctx = dict(self.env.context)
            ctx['location'] = data.location_id.id
            ctx['lot_id'] = data.lot_id.id
            if data.product_id.id and data.lot_id.id:
                filter = 'none'
            elif data.product_id.id:
                filter = 'product'
            else:
                filter = 'none'
            inventory = Inventory.create({
                'name': _('INV: %s') % tools.ustr(data.product_id.name),
                'filter': filter,
                'product_id': data.product_id.id,
                'location_id': data.location_id.id,
                'lot_id': data.lot_id.id})
            product = data.product_id.with_context(location=data.location_id.id, lot_id=data.lot_id.id)
            th_qty = product.qty_available
            line_data = {
                'inventory_id': inventory.id,
                'product_qty': data.new_quantity,
                'location_id': data.location_id.id,
                'product_id': data.product_id.id,
                'product_uom_id': data.product_id.uom_id.id,
                'theoretical_qty': th_qty,
                'prod_lot_id': data.lot_id.id
            }
            InventoryLine.create(line_data)
            inventory.action_done()
        return {}

    @api.onchange('location_id')
    def onchange_location_id(self):
        if self.location_id:
            qty = self.product_id.with_context(location=location_id)._product_available()
            if product_id in qty:
                self.new_quantity = qty[product_id]['qty_available']
