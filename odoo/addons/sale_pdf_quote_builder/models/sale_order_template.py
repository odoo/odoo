# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import api, fields, models

from odoo.addons.sale_pdf_quote_builder import utils


class SaleOrderTemplate(models.Model):
    _inherit = 'sale.order.template'

    sale_header = fields.Binary(
        string="Header pages", default=lambda self: self.env.company.sale_header)
    sale_header_name = fields.Char(default=lambda self: self.env.company.sale_header_name)
    sale_footer = fields.Binary(
        string="Footer pages", default=lambda self: self.env.company.sale_footer)
    sale_footer_name = fields.Char(default=lambda self: self.env.company.sale_footer_name)

    @api.constrains('sale_header')
    def _ensure_header_encryption(self):
        for template in self:
            if template.sale_header:
                utils._ensure_document_not_encrypted(base64.b64decode(template.sale_header))

    @api.constrains('sale_footer')
    def _ensure_footer_encryption(self):
        for template in self:
            if template.sale_footer:
                utils._ensure_document_not_encrypted(base64.b64decode(template.sale_footer))
