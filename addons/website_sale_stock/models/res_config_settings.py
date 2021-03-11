# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    inventory_availability = fields.Selection([
        ('always', 'Always'),
        ('never', 'Never'),
        ('threshold', 'Only below a threshold'),
    ], string='Inventory Availability', default='never')
    available_threshold = fields.Float(string='Availability Threshold')
    website_warehouse_id = fields.Many2one('stock.warehouse', related='website_id.warehouse_id', domain="[('company_id', '=', website_company_id)]", readonly=False)
    allow_order = fields.Selection([
        ('always', 'Always'),
        ('enough', 'Only if enough inventory'),
    ], string='Allow to Order', default='enough')
    availability_information = fields.Selection([
        ('quantity', 'Quantity Available'),
        ('state', 'In Stock - Quantity Left - Out of stock'),
        ('custom', 'Custom Message'),
    ], string="Availability Information", default="state")
    custom_message = fields.Char(string='Custom Message', default='Default Custom Message')

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        IrDefault = self.env['ir.default'].sudo()
        IrDefault.set('product.template', 'inventory_availability', self.inventory_availability)
        IrDefault.set('product.template', 'available_threshold', self.available_threshold if self.inventory_availability == 'threshold' else None)
        IrDefault.set('product.template', 'custom_message', self.custom_message if self.inventory_availability == 'custom' else None)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrDefault = self.env['ir.default'].sudo()
        res.update(inventory_availability=IrDefault.get('product.template', 'inventory_availability') or 'never',
                   available_threshold=IrDefault.get('product.template', 'available_threshold') or 5.0,
                   custom_message=IrDefault.get('product.template', 'custom_message') or '')
        return res

    @api.onchange('website_company_id')
    def _onchange_website_company_id(self):
        if self.website_warehouse_id.company_id != self.website_company_id:
            return {'value': {'website_warehouse_id': False}}
