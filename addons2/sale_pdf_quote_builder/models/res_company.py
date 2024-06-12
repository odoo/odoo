# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import api, fields, models

from odoo.addons.sale_pdf_quote_builder import utils


class ResCompany(models.Model):
    _inherit = 'res.company'

    sale_header = fields.Binary(string="Header pages")
    sale_header_name = fields.Char()
    sale_footer = fields.Binary(string="Footer pages")
    sale_footer_name = fields.Char()

    @api.constrains('sale_header')
    def _ensure_header_not_encrypted(self):
        for company in self:
            if company.sale_header:
                utils._ensure_document_not_encrypted(base64.b64decode(company.sale_header))

    @api.constrains('sale_footer')
    def _ensure_footer_not_encrypted(self):
        for company in self:
            if company.sale_footer:
                utils._ensure_document_not_encrypted(base64.b64decode(company.sale_footer))
