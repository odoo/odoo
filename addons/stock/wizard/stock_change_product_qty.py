# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models, api, tools, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, AccessError


class StockChangeProductQty(models.TransientModel):
    _name = "stock.change.product.qty"
    _description = "Change Product Quantity"

    product_id = fields.Many2one(comodel_name='product.product', string='Product', default=lambda self: self._context.get('active_id'))
    product_tmpl_id = fields.Many2one('product.template', 'Template', required=True)
    product_variant_count = fields.Integer(related='product_tmpl_id.product_variant_count', string='Variant Number')
    new_quantity = fields.Float('New Quantity on Hand', digits_compute=dp.get_precision('Product Unit of Measure'), required=True, help='This quantity is expressed in the Default Unit of Measure of the product.')
    lot_id = fields.Many2one(comodel_name='stock.production.lot', string='Serial Number', domain="[('product_id','=',product_id)]")
    location_id = fields.Many2one(comodel_name='stock.location', string='Location', required=True, domain="[('usage', '=', 'internal')]")

    @api.model
    def default_get(self, fields):
        """ To get default values for the object.
         @param self: The object pointer.
         @param fields: List of fields for which we want default values
         @return: A dictionary which of fields with values.
        """
        res = super(StockChangeProductQty, self).default_get(fields)

        if self._context.get('active_model') == 'product.template':
            product_id = self.env['product.product'].search([('product_tmpl_id', '=', self._context.get('active_id'))], limit=1)
            if product_id:
                res['product_id'] = product_id.id

        if 'location_id' in fields:
            location_id = res.get('location_id', False)
            if not location_id:
                try:
                    location_id = self.env.ref('stock.stock_location_stock').id
                except (AccessError):
                    pass
            if location_id:
                try:
                    self.env['stock.location'].browse([location_id]).check_access_rule('read')
                except (AccessError):
                    pass
            res['location_id'] = location_id
        return res

    @api.model
    def create(self, values):
        if values.get('product_id'):
            values.update(self.onchange_product_id_value(values['product_id'])['value'])
        return super(StockChangeProductQty, self).create(values)

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.product_tmpl_id = self.product_id.product_tmpl_id.id,
        self.product_variant_count = self.product_id.product_tmpl_id.product_variant_count

    def onchange_product_id_value(self, prod_id):
        product = self.env['product.product'].browse(prod_id)
        return {'value': {
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_variant_count': product.product_tmpl_id.product_variant_count
        }}

    @api.multi
    def change_product_qty(self):
        """ Changes the Product Quantity by making a Physical Inventory.
        @param self: The object pointer.
        @return:
        """
        for record in self:
            if record.new_quantity < 0:
                raise UserError(_('Quantity cannot be negative.'))
            if record.product_id.id and record.lot_id.id:
                filter = 'none'
            elif record.product_id.id:
                filter = 'product'
            else:
                filter = 'none'
            inventory = self.env['stock.inventory'].create({
                'name': _('INV: %s') % tools.ustr(record.product_id.name),
                'filter': filter,
                'product_id': record.product_id.id,
                'location_id': record.location_id.id,
                'lot_id': record.lot_id.id})
            theoretical_qty = record.product_id.with_context({'location': record.location_id.id, 'lot_id': record.lot_id.id}).qty_available
            line_data = {
                'inventory_id': inventory.id,
                'product_qty': record.new_quantity,
                'location_id': record.location_id.id,
                'product_id': record.product_id.id,
                'product_uom_id': record.product_id.uom_id.id,
                'theoretical_qty': theoretical_qty,
                'prod_lot_id': record.lot_id.id
            }
            self.env['stock.inventory.line'].create(line_data)
            inventory.action_done()
        return {}

    @api.multi
    @api.onchange('location_id', 'product_id')
    def onchange_location_id(self):
        if self.location_id:
            qty_wh = 0.0
            qty = self.product_id.with_context(location=self.location_id.id)._product_available()
            if self.product_id.id in qty:
                qty_wh = qty[self.product_id.id]['qty_available']
            return {'value': {'new_quantity': qty_wh}}
