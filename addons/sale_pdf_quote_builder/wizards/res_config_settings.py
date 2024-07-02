# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_header = fields.Binary(related='company_id.sale_header', readonly=False)
    sale_header_name = fields.Char(related='company_id.sale_header_name', readonly=False)
    sale_footer = fields.Binary(related='company_id.sale_footer', readonly=False)
    sale_footer_name = fields.Char(related='company_id.sale_footer_name', readonly=False)

    # === ACTION METHODS ===#

    def action_open_dynamic_fields_wizard(self):
        self.ensure_one()
        return {
            'name': _("Configure Dynamic Fields"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.pdf.quote.builder.dynamic.fields.wizard',
            'target': 'new',
        }
