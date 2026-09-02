# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Website(models.Model):
    _inherit = "website"

    def _compute_show_line_subtotals_tax_selection(self):
        ca_websites = self.filtered(
            lambda website: website.company_id.account_fiscal_country_id.code == "CA"
        )
        ca_websites.show_line_subtotals_tax_selection = "tax_excluded"
        return super(Website, self - ca_websites)._compute_show_line_subtotals_tax_selection()
