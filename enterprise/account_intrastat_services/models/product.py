# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # remove in master
    def _get_valid_intrastat_code_ids(self, valid_intrastat_codes):
        self.ensure_one()
        if 'service' in valid_intrastat_codes and self.type == 'service':
            return valid_intrastat_codes['service']
        return super()._get_valid_intrastat_code_ids(valid_intrastat_codes)

    @api.depends('type')
    def _compute_intrastat_code_domain(self):
        """Dynamically compute the domain for intrastat_code_id.
        Restricting to service codes only if services codes are available and product type is service"""
        service_codes_available = self.env["account.intrastat.code"].search_count(
            [
                ("country_id", "in", (self.env.company.account_fiscal_country_id.id, False)),
                ("type", "=", "service"),
            ],
            limit=1,
        )
        for product in self:
            code_type = 'service' if service_codes_available and product.type == 'service' else 'commodity'
            product.intrastat_code_domain = str([
                ("country_id", "in", (self.env.company.account_fiscal_country_id.id, False)),
                ("type", "=", code_type),
            ])
