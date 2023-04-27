# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    inventory_availability = fields.Selection([
        ('never', 'Sell regardless of inventory'),
        ('always', 'Show inventory on website and prevent sales if not enough stock'),
        ('threshold', 'Show inventory when below the threshold and prevent sales if not enough stock'),
        ('custom', 'Show product-specific notifications'),
    ], string='Inventory Availability', default='never')
    available_threshold = fields.Float(string='Availability Threshold')
    website_warehouse_id = fields.Many2one('stock.warehouse', related='website_id.warehouse_id', domain="[('company_id', '=', website_company_id)]", readonly=False)

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        IrDefault = self.env['ir.default'].sudo()
        IrDefault.set('product.template', 'inventory_availability', self.inventory_availability)
        IrDefault.set('product.template', 'available_threshold', self.available_threshold if self.inventory_availability == 'threshold' else None)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrDefault = self.env['ir.default'].sudo()
        res.update(inventory_availability=IrDefault.get('product.template', 'inventory_availability') or 'never',
                   available_threshold=IrDefault.get('product.template', 'available_threshold') or 5.0)
        return res

    @api.onchange('website_company_id')
    def _onchange_website_company_id(self):
        if self.website_warehouse_id.company_id != self.website_company_id:
            return {'value': {'website_warehouse_id': False}}
