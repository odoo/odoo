# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    available_threshold = fields.Float(string='Availability Threshold')
    website_warehouse_id = fields.Many2one('stock.warehouse', related='website_id.warehouse_id', domain="[('company_id', '=', website_company_id)]", readonly=False)
    allow_order = fields.Selection([
        ('always', 'Always'),
        ('enough', 'Only if enough inventory'),
    ], string='Allow Orders', default='enough')
    in_stock = fields.Html(string="In Stock", translate=True, default="""<i class="text-success fa fa-check"/> <span style="color:green">In stock</span>""")
    below_threshold = fields.Html(string="Below Threshold", translate=True, default="""<i class="text-warning fa fa-exclamation-triangle"/> <span style="color:orange">Only {qty_available} {uom_name} left</span>""")
    no_stock = fields.Html(string="No Stock", translate=True, default="""<i class="text-danger fa fa-remove"/> <span style="color:red">Out Of Stock</span>""")

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        IrDefault = self.env['ir.default'].sudo()
        IrDefault.set('product.template', 'available_threshold', self.available_threshold)
        IrDefault.set('product.template', 'no_stock', self.no_stock)
        IrDefault.set('product.template', 'below_threshold', self.below_threshold)
        IrDefault.set('product.template', 'in_stock', self.in_stock)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrDefault = self.env['ir.default'].sudo()
        res.update(available_threshold=IrDefault.get('product.template', 'available_threshold') or 5.0,
                   no_stock=IrDefault.get('product.template', 'no_stock') or 'Out of Stock',
                   below_threshold=IrDefault.get('product.template', 'below_threshold') or 'Only {qty} {unit} left',
                   in_stock=IrDefault.get('product.template', 'in_stock') or 'In Stock',)
        return res

    @api.onchange('website_company_id')
    def _onchange_website_company_id(self):
        if self.website_warehouse_id.company_id != self.website_company_id:
            return {'value': {'website_warehouse_id': False}}
