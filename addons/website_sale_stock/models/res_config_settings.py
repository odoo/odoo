# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    allow_out_of_stock_order = fields.Boolean(
        string='Continue selling when out-of-stock',
        default=True)
    available_threshold = fields.Float(
        string='Show Threshold',
        default=5.0)
    show_availability = fields.Boolean(
        string='Show availability Qty',
        default=False)
    website_warehouse_id = fields.Many2one(
        'stock.warehouse',
        related='website_id.warehouse_id',
        domain="[('company_id', '=', website_company_id)]",
        readonly=False)

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        IrDefault = self.env['ir.default'].sudo()

        IrDefault.set('product.template', 'allow_out_of_stock_order', self.allow_out_of_stock_order)
        IrDefault.set('product.template', 'available_threshold', self.available_threshold)
        IrDefault.set('product.template', 'show_availability', self.show_availability)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrDefault = self.env['ir.default'].sudo()
        allow_out_of_stock_order = IrDefault.get('product.template', 'allow_out_of_stock_order')

        res.update(
            allow_out_of_stock_order=allow_out_of_stock_order if allow_out_of_stock_order is not None else True,
            available_threshold=IrDefault.get('product.template', 'available_threshold') or 5.0,
            show_availability=IrDefault.get('product.template', 'show_availability') or False)
        return res
