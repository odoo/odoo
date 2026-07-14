# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Website(models.Model):
    _inherit = 'website'

    @api.model_create_multi
    def create(self, vals_list):
        for website in vals_list:
            if website.get('company_id') and self.env['res.company'].browse(website['company_id']).country_code == "BR":
                website.setdefault('show_line_subtotals_tax_selection', 'tax_included')
        return super().create(vals_list)

    def _display_partner_b2b_fields(self):
        """ Brazil localization must always display b2b fields. """
        return self.company_id.country_id.code == 'BR' or super()._display_partner_b2b_fields()
