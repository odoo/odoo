# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, tools, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class ProductChangeQuantity(models.TransientModel):
    _name = "stock.change.product.qty"
    _description = "Change Product Quantity"

    # TDE FIXME: strange dfeault method, was present before migration ? to check
    product_id = fields.Many2one('product.product', 'Product', required=True)
    product_tmpl_id = fields.Many2one('product.template', 'Template', required=True)
    product_variant_count = fields.Integer('Variant Count', related='product_tmpl_id.product_variant_count', readonly=False)
    new_quantity = fields.Float(
        'New Quantity on Hand', default=1,
        digits=dp.get_precision('Product Unit of Measure'), required=True,
        help='This quantity is expressed in the Default Unit of Measure of the product.')
    location_id = fields.Many2one('stock.location', 'Location', required=True, domain="[('usage', '=', 'internal')]")

    @api.model
    def default_get(self, fields):
        res = super(ProductChangeQuantity, self).default_get(fields)
        if 'location_id' in fields and not res.get('location_id'):
            company_user = self.env.user.company_id
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
            if warehouse:
                res['location_id'] = warehouse.lot_stock_id.id
        return res

    @api.onchange('location_id', 'product_id')
    def onchange_location_id(self):
        # TDE FIXME: should'nt we use context / location ?
        if self.location_id and self.product_id:
            availability = self.product_id.with_context(compute_child=False)._product_available()
            self.new_quantity = availability[self.product_id.id]['qty_available']

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.product_tmpl_id = self.onchange_product_id_dict(self.product_id.id)['product_tmpl_id']

    def _action_start_line(self):
        product = self.product_id.with_context(location=self.location_id.id)
        th_qty = product.qty_available

        res = {
               'product_qty': self.new_quantity,
               'location_id': self.location_id.id,
               'product_id': self.product_id.id,
               'product_uom_id': self.product_id.uom_id.id,
               'theoretical_qty': th_qty,
        }

        return res


    def onchange_product_id_dict(self, product_id):
        return {
            'product_tmpl_id': self.env['product.product'].browse(product_id).product_tmpl_id.id,
        }

    @api.model
    def create(self, values):
        if values.get('product_id'):
            values.update(self.onchange_product_id_dict(values['product_id']))
        return super(ProductChangeQuantity, self).create(values)

    @api.constrains('new_quantity')
    def check_new_quantity(self):
        if any(wizard.new_quantity < 0 for wizard in self):
            raise UserError(_('Quantity cannot be negative.'))

    def change_product_qty(self):
        """ Changes the Product Quantity by making a Physical Inventory. """
        Inventory = self.env['stock.inventory']
        for wizard in self:
            product = wizard.product_id.with_context(location=wizard.location_id.id)
            line_data = wizard._action_start_line()

            if wizard.product_id.id:
                inventory_filter = 'product'
            else:
                inventory_filter = 'none'
            inventory = Inventory.create({
                'name': _('INV: %s') % tools.ustr(wizard.product_id.display_name),
                'filter': inventory_filter,
                'product_id': wizard.product_id.id,
                'location_id': wizard.location_id.id,
                'line_ids': [(0, 0, line_data)],
            })
            inventory.action_validate()
        return {'type': 'ir.actions.act_window_close'}
