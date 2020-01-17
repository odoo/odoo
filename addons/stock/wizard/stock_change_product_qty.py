# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductChangeQuantity(models.TransientModel):
    _name = "stock.change.product.qty"
    _description = "Change Product Quantity"

    product_id = fields.Many2one('product.product', 'Product', required=True)
    product_tmpl_id = fields.Many2one('product.template', 'Template', required=True)
    product_variant_count = fields.Integer('Variant Count',
        related='product_tmpl_id.product_variant_count', readonly=False)
    new_quantity = fields.Float(
        'New Quantity on Hand', default=1,
        digits='Product Unit of Measure', required=True,
        help='This quantity is expressed in the Default Unit of Measure of the product.')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.new_quantity = self.product_id.qty_available

    @api.constrains('new_quantity')
    def check_new_quantity(self):
        if any(wizard.new_quantity < 0 for wizard in self):
            raise UserError(_('Quantity cannot be negative.'))

    def change_product_qty(self):
        """ Changes the Product Quantity by creating/editing corresponding quant.
        """
        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1
        )
        # Before creating a new quant, the quand `create` method will check if
        # it exists already. If it does, it'll edit its `inventory_quantity`
        # instead of create a new one.
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_id.id,
            'location_id': warehouse.lot_stock_id.id,
            'inventory_quantity': self.new_quantity,
        })
        return {'type': 'ir.actions.act_window_close'}
