# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import _, fields, models

from odoo.addons.sale_pdf_quote_builder import utils


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_header = fields.Binary(related='company_id.sale_header', readonly=False)
    sale_header_name = fields.Char(related='company_id.sale_header_name', readonly=False)
    sale_footer = fields.Binary(related='company_id.sale_footer', readonly=False)
    sale_footer_name = fields.Char(related='company_id.sale_footer_name', readonly=False)

    # === ACTION METHODS ===#

    def action_open_dynamic_fields_configurator_wizard(self):
        self.ensure_one()
        valid_form_fields = set()
        if self.sale_header:
            valid_form_fields.update(utils._get_valid_form_fields(self.sale_header))
        if self.sale_footer:
            valid_form_fields.update(utils._get_valid_form_fields(self.sale_footer))
        default_form_fields = {'header_footer': list(valid_form_fields)}
        return {
            'name': _("Whitelist PDF Fields"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.pdf.quote.builder.dynamic.fields.wizard',
            'target': 'new',
            'context': {'default_current_form_fields': json.dumps(default_form_fields)},
        }
