from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _get_company_registry_placeholder(self, country_code):
        if country_code == 'FR':
            return '12345678900001'  # SIRET
        return super()._get_company_registry_placeholder(country_code)
