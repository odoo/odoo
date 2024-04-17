# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json

from odoo import _, api, fields, models

from odoo.addons.sale_pdf_quote_builder import utils


class SaleOrderTemplate(models.Model):
    _inherit = 'sale.order.template'

    sale_header = fields.Binary(
        string="Header pages", default=lambda self: self.env.company.sale_header)
    sale_header_name = fields.Char(default=lambda self: self.env.company.sale_header_name)
    sale_footer = fields.Binary(
        string="Footer pages", default=lambda self: self.env.company.sale_footer)
    sale_footer_name = fields.Char(default=lambda self: self.env.company.sale_footer_name)

    # === CONSTRAINT METHODS ===#

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

    # === ACTION METHODS ===#

    def action_open_dynamic_fields_configurator_wizard(self):
        self.ensure_one()
        valid_form_fields = set()
        if self.sale_header:
            valid_form_fields.update(utils._get_form_fields_from_pdf(self.sale_header))
        if self.sale_footer:
            valid_form_fields.update(utils._get_form_fields_from_pdf(self.sale_footer))
        default_form_fields = {'header_footer': list(valid_form_fields)}
        return {
            'name': _("Configure Dynamic Fields"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.pdf.quote.builder.dynamic.fields.wizard',
            'target': 'new',
            'context': {'default_current_form_fields': json.dumps(default_form_fields)},
        }
