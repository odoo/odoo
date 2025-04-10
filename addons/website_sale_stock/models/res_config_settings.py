# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.tools.translate import html_translate


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    allow_out_of_stock_order = fields.Boolean(
        string='Continue selling when out-of-stock',
        default=True)
    out_of_stock_message = fields.Html(string="Out-of-Stock Message", translate=html_translate)
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
        IrDefault.set('product.template', 'out_of_stock_message', self.out_of_stock_message)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrDefaultGet = self.env['ir.default'].sudo()._get
        allow_out_of_stock_order = IrDefaultGet('product.template', 'allow_out_of_stock_order')

        res.update(
            allow_out_of_stock_order=allow_out_of_stock_order if allow_out_of_stock_order is not None else True,
            out_of_stock_message=IrDefaultGet('product.template', 'out_of_stock_message') or '',
            available_threshold=IrDefaultGet('product.template', 'available_threshold') or 5.0,
            show_availability=IrDefaultGet('product.template', 'show_availability') or False)
        return res
