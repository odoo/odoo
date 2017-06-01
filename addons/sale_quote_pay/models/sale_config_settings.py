# -*- coding: utf-8 -*-

from odoo import models, fields

class SaleConfigSettings(models.TransientModel):
    _inherit = 'sale.config.settings'

    sale_quote_type = fields.Selection([
        ('signature', 'Signature'),
        ('payment', 'Payment'),
    ], string="Quotation Signature & Payment", default='signature')

    def set_sale_quote_type_defaults(self):
        return self.env['ir.values'].sudo().set_default('sale.config.settings', 'sale_quote_type', self.sale_quote_type)
