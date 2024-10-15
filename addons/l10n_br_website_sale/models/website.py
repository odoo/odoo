# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models
from odoo.addons import website_sale


class Website(website_sale.Website):

    @api.model_create_multi
    def create(self, vals_list):
        for website in vals_list:
            if website.get('company_id') and self.env['res.company'].browse(website['company_id']).country_code == "BR":
                website.setdefault('show_line_subtotals_tax_selection', 'tax_included')
        return super().create(vals_list)
