from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.depends('country_id.code', 'ref_company_ids.account_fiscal_country_id.code')
    def _compute_company_registry_placeholder(self):
        super()._compute_company_registry_placeholder()
        for partner in self:
            country = partner.ref_company_ids[:1].account_fiscal_country_id or partner.country_id
            if country.code == 'FR':
                partner.company_registry_placeholder = '12345678900001'  # SIRET
